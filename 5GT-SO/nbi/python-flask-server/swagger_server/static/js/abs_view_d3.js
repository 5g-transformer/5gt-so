function representation(rawData) {
    //find the node index, in case some missing index in the json
    function find(f) {
            var i = -1
            rawData.nodes.forEach(function(node, index) {
                if (node.id == f)
                    i = index;
            });
            return i;
        }
        //set teh source and target index
    rawData.links.forEach(function(d) {
            d.source = find(d.source);
            d.target = find(d.target);
        })
        // console.log(rawData);
    var chartDiv = document.getElementById("chartd3");
    var h = chartDiv.clientHeight - 16,
        /*h = 600,*/
        w = chartDiv.clientWidth,
        fill = d3.scale.category20();

    //console.log(w, h, chartDiv.clientWidth, chartDiv.clientHeight, chartDiv);
    var vis = d3.select("#chartd3")
        .append("svg")
        .attr("width", "100%")
        .attr("height", h);

    var force = d3.layout.force()
        .charge(-500)
        //.linkDistance(200)
        .linkDistance(function(link) {
            return link.length;
        })
        //.linkStrength(0.1)
        .nodes(rawData.nodes)
        .links(rawData.links)
        .size([w, h])
        .start();

    // Define the div for the tooltip
    var tooltip = d3.select("body").append("div")
        .attr("class", "tooltip")
        .style("opacity", 0);

    var path = vis.append("svg:g").selectAll("path")
        .data(force.links())
        .enter().append("svg:path")
        .attr("class", function(d) {
            return "link";
        })
        .on("mouseover", function(d) {
            tooltip.transition()
                .duration(200)
                .style("opacity", .9);
            if (typeof d.llid !== 'undefined') {
                tooltip.html("LL_ID: " + d.llid)
                    .style("left", (d3.event.pageX + 10) + "px")
                    .style("top", (d3.event.pageY - 18) + "px");
            }
        })
        .on("mouseout", function(d) {
            tooltip.transition()
                .duration(500)
                .style("opacity", 0);
        });

    function dragend(d) {
      d3.select(this).classed("fixed", d.fixed = false);
    }

    function dragstart(d) {
      d3.select(this).classed("fixed", d.fixed = true);
    }
    var inner_drag = force.drag()
        .on("dragstart", dragstart);

    var node = vis.selectAll(".node")
        .data(rawData.nodes)
        .enter().append("g")
        .attr("class", "node")
        //    .on("dblclick", function(d,i) { if (d.type === "NFVIPOP") {
        //        alert('Nfvi Pop Id: '+ d.name + '\nZone Id:' + d.zone_id + '\nGeo Location: ' + d.geo_location);
        //    } else {
        //        alert('GW: ' + d.name);
        //    }})
        .on("dblclick", dragend)
        .on("mouseover", function(d) {
            tooltip.transition()
                .duration(700)
                .style("opacity", .9);

            if (d.type === 'NFVIPOP') {
                tooltip.html(" NFVIPOP: " + d.name + "<br> GeoLocation: " + d.geo_location + "<br> Zone: " + d.zone_name)
                    .style("left", (d3.event.pageX + 20) + "px")
                    .style("top", (d3.event.pageY - 28) + "px");
            } else if (d.type === 'NFVIPOP-Fed') {
                tooltip.html(" NFVIPOP Fed: " + d.name + "<br> GeoLocation: " + d.geo_location)
                    .style("left", (d3.event.pageX + 20) + "px")
                    .style("top", (d3.event.pageY - 28) + "px");
            } else {
                tooltip.html('GW: ' + d.name)
                    .style("left", (d3.event.pageX + 20) + "px")
                    .style("top", (d3.event.pageY - 28) + "px");
            }
        })
        .on("mouseout", function(d) {
            tooltip.transition()
                .duration(500)
                .style("opacity", 0);
        })
        .call(inner_drag);

    node.append("image")
        //.attr("xlink:href", "/static/images/pop5.png")
        .attr("xlink:href", function(d) {
            return d.img;
        })
        .attr("x", -15)
        .attr("y", -15)
        .attr("width", 30)
        .attr("height", 30);


    var text = vis.selectAll(".text")
        .data(rawData.nodes)
        .enter().append("text")
        //.style("font", "12px helvetica")
        .attr("x", function(d) {
            return d.x;
        })
        .attr("y", function(d) {
            if (d.type == "NFVIPOP") {
                return d.y - 16;
            } else {
                return d.y - 11;
            }
        })
        .text(function(d) {
            return d.name;
        })
        //.call(force.drag)
        ;

    vis.style("opacity", 1e-6)
        .transition()
        .duration(1000)
        .style("opacity", 1)
        .style("align", "center")
        .style("border", 2);

    function max_key(d) {
        var max_value = 0;
        d.forEach(function(e) {
            if (e.key > max_value) {
                max_value = e.key;
            }
        });
        return max_value + 1;
    }
    max_links = max_key(rawData.links);

    force.on("tick", function() {
        path.attr("d", function(d) {
            var dx = d.target.x - d.source.x,
                dy = d.target.y - d.source.y,
                dr = 300 / (d.key * (2.5 / max_links) + 1);
            //dr = Math.sqrt(x * dx + dy * dy) + 2500*d.key;
            //mx = d.source.x + dx,
            //my = d.source.y + dy;
            //return ["M",d.source.x,d.source.y,"A",dr,dr,0,0,1,mx,my,"A",dr,dr,0,0,1,d.target.x,d.target.y].join(" ");
            return "M" + d.source.x + "," + d.source.y + "A" + dr + "," + dr + " 0 0,1 " + d.target.x + "," + d.target.y;

        });



        node.attr("transform", function(d) {
            return "translate(" + d.x + "," + d.y + ")";
        });

        text.attr("x", function(d) {
                return d.x;
            })
            .attr("y", function(d) {
                if (d.type == "NFVIPOP") {
                    return d.y - 16;
                } else {
                    return d.y - 11;
                }
            });
    });

    //Legend
    var legend = vis.selectAll(".legend")
        .data([{
            "group": 1,
            "name": "NFVIPOP",
            "link": "/static/images/pop5.png"
        }, {
            "group": 2,
            "name": "GW",
            "link": "/static/images/router.png"
        }, {
            "group": 3,
            "name": "NFVIPOP-Fed",
            "link": "/static/images/pop_fed.png"
        }])
        .enter().append("g")
        .attr("class", "legend")
        .attr("transform", function(d, i) {
            return "translate(0," + i * 30 + ")";
        });
    //console.log(fill.domain());

    legend.append("image")
        //.attr("xlink:href", "/static/images/pop5.png")
        .attr("xlink:href", function(d) {
            return d.link;
        })
        .attr("x", w - 72)
        .attr("y", 0)
        .attr("width", 30)
        .attr("height", 30);

    legend.append("text")
        .attr("x", w - 74)
        .attr("y", 15)
        .attr("dy", ".35em")
        .style("text-anchor", "end")
        .text(function(d) {
            return d.name
        });
}