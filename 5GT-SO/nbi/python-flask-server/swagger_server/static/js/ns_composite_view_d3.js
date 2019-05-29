function representation(rawData) {
    // console.log(rawData.nodes);
    //// ASSUMPTION: COMPOSITE SERVICE IS MADE BY ONLY 2 NESTED
    var groups_nested = d3.nest().key(function(d) {
        return d.nested[0];
    }).entries(rawData.nodes);
    var groups_nested_2 = d3.nest().key(function(d) {
        return d.nested[1];
    }).entries(rawData.nodes);

    // merging all the existing object in 2nd group to the first one
    groups_nested_2.forEach(function (element) {
        groups_nested.forEach( function (nes) {
            if (element['key'] === nes['key']) {
                element['values'].forEach(function (ob) {
                    nes['values'].push(ob);
                });
            }

        });
    });
//    console.log("Groups_nested", groups_nested);
//    console.log("Groups_nested_2", groups_nested_2);

    var groups_placement = d3.nest().key(function(d) {
        return d.placement_element;
    }).entries(rawData.nodes);

    // removing "undefined" key in the group placement
    var groups_placement_filtered = groups_placement.filter(function(d) { return d.key !== 'undefined'; });

    var groups_federation = d3.nest().key(function(d) {
        return d.federation[0];
    }).entries(rawData.nodes);

    var groups_federation_2 = d3.nest().key(function(d) {
        return d.federation[1];
    }).entries(rawData.nodes);

    // merging all the existing object in 2nd group to the first one
    groups_federation_2.forEach(function (element) {
        groups_federation.forEach( function (fed) {
            if (element['key'] === fed['key']) {
                element['values'].forEach(function (ob) {
                    fed['values'].push(ob);
                });
            }

        });
    });

    var groupPath_nested = function(d) {
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

    var groupPath_placement = function(d) {
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

    var groupPath_federation = function(d) {
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
    var chartDiv = document.getElementById("chartd3");

    var /*h = 300,*/
        h = chartDiv.clientHeight - 16,
        w = chartDiv.clientWidth,
        fill = d3.scale.category20();
    var vis = d3.select("#chartd3")
        .append("svg")
        .attr("width", "100%")
        .attr("height", h);

    var t_fill = [textures.lines().thicker(),
                  textures.circles().thicker(),
                  textures.paths().d("squares").size(8),
                  textures.paths().d("hexagons").size(8),
                  textures.paths().d("crosses").lighter().thicker(),
                  textures.paths().d("caps").lighter().thicker(),
                  textures.paths().d("woven").lighter().thicker(),
                  textures.paths().d("waves").thicker().stroke("firebrick")];
    t_fill.forEach(function (t) {
        vis.call(t);
    });
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

    var hull_nested = vis.selectAll("path.hull_nested")
        .data(groups_nested)
        .enter().insert("path", "g.node")
        .attr("class", "hull_nested")
        .style("fill", groupFill)
        .style("stroke", groupFill)
        .style("stroke-width", "40px")
        .style("stroke-linejoin", "round")
        .style("opacity", .5)
        .attr("d", groupPath_nested);

    var hull_placement = vis.selectAll("path.hull_placement")
        .data(groups_placement_filtered)
        .enter().insert("path", "g.node")
        .attr("class", "hull_placement")
//        .style("fill", groupFill)
//        .style("stroke", groupFill)
        .style("fill", function(d, i) {
            return t_fill[i].url();
        })
        .style("stroke", function(d, i) {
            return t_fill[i].url();
        })
        .style("stroke-width", "40px")
        .style("stroke-linejoin", "round")
        .style("opacity", 0)
        .attr("d", groupPath_placement);

    //console.log("paht.hull_placement: " , hull_placement);

    var hull_federation = vis.selectAll("path.hull_federation")
        .data(groups_federation)
        .enter().insert("path", "g.node")
        .attr("class", "hull_federation")
        .style("fill", groupFill)
        .style("stroke", groupFill)
        .style("stroke-width", "80px")
        .style("stroke-linejoin", "round")
        .style("opacity", 0)
        .attr("d", groupPath_federation);

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

        hull_nested.attr("d", groupPath_nested);
        hull_placement.attr("d", groupPath_placement);
        hull_federation.attr("d", groupPath_federation);
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

    var list_placement = [];
    groups_placement_filtered.forEach(function (t){
        list_placement.push(t['key']);
    });
    //console.log(list_placement);
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

        var legend_texture = vis.selectAll(".legend2")
        .data(list_placement)
        .enter().append("g")
        .attr("class", "legend2")
        .attr("transform", function(d, i) {
            return "translate(0," + (fill.domain().length * 20 + i * 20) + ")";
        });

    //Legend for textured hull element (placement info)
    legend_texture.append("circle")
        .attr("cx", w - 47)
        .attr("cy", 8.5)
        .attr("r", 7.5)
        .style("opacity", 0.5)
        .style("fill", function(d, i) {
            return t_fill[i].url();
        });

    legend_texture.append("text")
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

// A function that update the color of the circle
function updateHulls(mychoice) {
    h_placement = d3.select("#chartd3").selectAll("path.hull_placement");
    h_nested = d3.select("#chartd3").selectAll("path.hull_nested");
    h_federation = d3.select("#chartd3").selectAll("path.hull_federation");
    // console.log(h_placement, h_nested);
    if (mychoice === 'nested_ns') {
        h_nested.transition().duration(750).style("opacity", 0.5);
        h_placement.transition().duration(750).style("opacity", 0);
        h_federation.transition().duration(750).style("opacity", 0);
    } else if (mychoice === 'placement_info') {
        h_nested.transition().duration(750).style("opacity", 0);
        h_placement.transition().duration(750).style("opacity", 0.5);
        h_federation.transition().duration(750).style("opacity", 0.5);
    } else {
        h_nested.transition().duration(750).style("opacity", 0);
        h_placement.transition().duration(750).style("opacity", 0);
        h_federation.transition().duration(750).style("opacity", 0.5);
    }
}