function representation(rawData) {
    //console.log(rawData.nodes);
    var groups = d3.nest().key(function(d) {
        return d.placement_element;
    }).entries(rawData.nodes);

    for (var i = 0; i < groups.length; i++){
        if (groups[i]['key'] === "undefined") {
            groups.splice(i, 1);
        }
    }

    var groupPath = function(d) {
        var fakePoints = [];
        if (d.values.length == 1)
        {
            var dx = d.values[0].x;
            var dy = d.values[0].y;
            mx = dx * 0.00001; my = dy * 0.00001;
            fakePoints = [[dx + my, dy - mx], [dx - my, dy + mx], [dx - 2*my, dy + 2*mx] ];
        }
        if (d.values.length == 2)
        {
            var dx = d.values[1].x - d.values[0].x;
            var dy = d.values[1].y - d.values[0].y;
            dx *= 0.00001; dy *= 0.00001;
            var mx = (d.values[0].x + d.values[1].x) * 0.5;
            var my = (d.values[0].y + d.values[1].y) * 0.5;
            fakePoints = [[mx + dy, my - dx], [mx - dy, my + dx]];
        }
        return "M" +
            d3.geom.hull(d.values.map(function(i) { return [i.x, i.y]; })
            // append the fakePoints to the input data
            .concat(fakePoints))
            .join("L") + "Z";
    }

    var groupFill = function(d, i) {
        return fill(d.key);
    };
    // console.log(groups);
    var chartDiv = document.getElementById("chartd3");

    var /*h = 300,*/
        h = chartDiv.clientHeight - 16,
        w = chartDiv.clientWidth,
        fill = d3.scale.category20();

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

    // Define the div for the tooltip
    var tooltip = d3.select("body").append("div")
        .attr("class", "tooltip")
        .style("opacity", 0);

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

    var node = vis.selectAll("node")
        .data(rawData.nodes)
        .enter().append("g")
        .attr("class", "node")
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

    var hull = vis.selectAll("path.hull")
        .data(groups)
        .enter().insert("path", "g.node")
        .attr("class", "hull")
        .style("fill", groupFill)
        .style("stroke", groupFill)
        .style("stroke-width", "40px")
        .style("stroke-linejoin", "round")
        .style("opacity", .5)
        .attr("d", groupPath)
        .on("mouseover", function(d) {
            tooltip.transition()
                .duration(700)
                .style("opacity", .9);
            tooltip.html(" Placement: " + d.key)
                .style("left", (d3.event.pageX + 20) + "px")
                .style("top", (d3.event.pageY - 28) + "px");
        })
        .on("mouseout", function(d) {
            tooltip.transition()
                .duration(500)
                .style("opacity", 0);
        });

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

        hull.attr("d", groupPath);
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
        .style("opacity", function(d) {
            if (d == "VNFD" || d == "VLD") {
                return 1.0;
            } else {
            return 0.5;
            }
        })
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