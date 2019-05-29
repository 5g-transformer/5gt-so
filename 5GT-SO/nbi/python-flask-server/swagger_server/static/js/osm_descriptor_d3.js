function representation(rawData, descr_type) {
    // console.log( rawData);
    var chartDiv = document.getElementById("chartd3");
    if (descr_type == 'nsd'){
        blue_colors = ['#3182bd', '#6baed6', '#9ecae1', '#c6dbe'];
        fill = d3.scale.ordinal().range(blue_colors);
    } else if (descr_type == 'vnfd') {
        green_colors = ['#004c00', '#00b200','#00e500'];
        fill = d3.scale.ordinal().range(green_colors);
    } else {
        red_colors = ['#660000', '#b20000', '#e50000'];
        fill = d3.scale.ordinal().range(red_colors);
    }

    var /*h = 300,*/
        h = chartDiv.clientHeight - 16,
        w = chartDiv.clientWidth,
        // fill = d3.scale.category20();
        fill;
    //console.log(w, h, chartDiv.clientWidth, chartDiv.clientHeight, chartDiv);

    var vis = d3.select("#chartd3")
        .append("svg")
        .attr("width", "100%")
        .attr("height", h);

    var force = d3.layout.force()
        .charge(function(node) {
            return node.graph === 0 ? -30 : -300;
        })
        .linkDistance(100)
        .linkStrength(0.1)
        .nodes(rawData.nodes)
        .links(rawData.links)
        .size([w, h])
        .start();

    var link = vis.selectAll("lined3.link")
        .data(rawData.links)
        .enter().append("svg:line")
        .attr("class", "link")
        .style("stroke-width", 5)
        .style("stroke", "gray")
        .attr("x1", function(d) {
            return d.source.x;
        })
        .attr("y1", function(d) {
            return d.source.y;
        })
        .attr("x2", function(d) {
            return d.target.x;
        })
        .attr("y2", function(d) {
            return d.target.y;
        });

    //var node = vis.selectAll("circled3.node")
    //  .data(rawData.nodes)
    //.enter().append("circle")
    //.attr("class", "node")
    //.attr("cx", function(d) { return d.x; })
    //.attr("cy", function(d) { return d.y; })
    //.attr("r", 7.5)
    //.style("fill", function(d) { return fill(d.type); })
    //.on("dblclick", function(d,i) { alert('Features: \n'+ d.features); })
    //.call(force.drag);

    function dragend(d) {
      d3.select(this).classed("fixed", d.fixed = false);
    }

    function dragstart(d) {
      d3.select(this).classed("fixed", d.fixed = true);
    }
    var inner_drag = force.drag()
        .on("dragstart", dragstart);

    var node = vis.append("g")
        .attr("class", "nodes")
        .selectAll(".node")
        .data(rawData.nodes)
        .enter().append("g")
        .style("fill", function(d) {
            return fill(d.type);
        })
        .attr("class", "node")
//        .on("dblclick", function(d, i) {
//            alert('Features: \n' + d.features);
//        })
        .on("dblclick", dragend)
        .call(inner_drag);

    node.each(function(d) {
        if (d.shape == "circle") {
            d3.select(this).append("circle")
                .attr("r", 12.5);
        } else {
            d3.select(this).append("rect")
                .attr("height", 16)
                .attr("width", 35)
                .attr("y", -(16 / 2))
                .attr("x", -(35 / 2));
        }

    });

    var text = vis.selectAll("circled3.text")
        .data(rawData.nodes)
        .enter().append("text")
        //.style("font", "12px helvetica")
        .attr("x", function(d) {
            return d.x;
        })
        .attr("y", function(d) {
            return d.y - 15;
        })
        .text(function(d) {
            return d.name;
        });
        //.call(force.drag)

    vis.style("opacity", 1e-6)
        .transition()
        .duration(1000)
        .style("opacity", 1)
        .style("align", "center")
        .style("border", 2);

    force.on("tick", function() {
        link.attr("x1", function(d) {
                return d.source.x;
            })
            .attr("y1", function(d) {
                return d.source.y;
            })
            .attr("x2", function(d) {
                return d.target.x;
            })
            .attr("y2", function(d) {
                return d.target.y;
            });

        //node.attr("cx", function(d) { return d.x; })
        //   .attr("cy", function(d) { return d.y; });
        node.attr("transform", function(d) {
            return "translate(" + d.x + "," + d.y + ")";
        });
        text.attr("x", function(d) {
                return d.x;
            })
            .attr("y", function(d) {
                return d.y - 15;
            });
    });

    //Legend
    var legend = vis.selectAll(".legend")
        .data(fill.domain())
        .enter().append("g")
        .attr("class", "legend")
        .attr("transform", function(d, i) {
            return "translate(0," + i * 20 + ")";
        });

    legend.append("circle")
        .attr("cx", w - 47)
        .attr("cy", 8.5)
        .attr("r", 7.5)
        .style("fill", fill);

    legend.append("text")
        .attr("x", w - 59)
        .attr("y", 9)
        .attr("dy", ".35em")
        .style("text-anchor", "end")
        .text(function(d) {
            return d
        });
}

// Remove force layout and data
function remove_graph(){
    d3.select("svg").remove();
}