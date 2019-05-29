var rawData = {{ yaml_network|tojson }}
// console.log(rawData);
var chartDiv = document.getElementById("chartd3");
var h = 300,
    /* h = chartDiv.clientHeight,*/
    w = chartDiv.clientWidth,
    fill = d3.scale.category20();
//console.log(w, h, chartDiv.clientWidth, chartDiv.clientHeight, chartDiv);
var vis = d3.select("#chartd3")
    .append("svg")
    .attr("width", "100%")
    .attr("height", h);

var force = d3.layout.force()
    .charge(function(node) {return node.graph === 0 ? -30 : -300;})
    .linkDistance(100)
    .linkStrength(0.1)
    .nodes(rawData.nodes)
    .links(rawData.links)
    .size([w, h])
    .start();


var path = vis.append("svg:g").selectAll("path")
    .data(force.links())
    .enter().append("svg:path")
    .style("stroke-width", 5)
    .style("stroke", "gray")
    .style("fill", "none")
    .attr("class", function(d) { return "link " + d.type; })
    .attr("marker-mid", function(d) { return "url(#" + d.type + ")"; });

var node = vis.selectAll(".node")
    .data(rawData.nodes)
    .enter().append("g")
    .attr("class", "node")
    .on("dblclick", function(d,i) { alert('Nfvi Pop Id: '+ d.nfvi_pop_id + '\nZone Id:' + d.zone_id + '\nZone Name: ' + d.zone_name); })
    .call(force.drag);

node.append("image")
    .attr("xlink:href", "static/favicon_cttc_blue.ico")
    .attr("x", -8)
    .attr("y", -8)
    .attr("width", 16)
    .attr("height", 16);

node.append("text")
    .attr("dx", 12)
    .attr("dy", ".35em")
    .text(function (d) {
    return d.name
});


var text = vis.selectAll(".text")
    .data(rawData.nodes)
    .enter().append("text")
    //.style("font", "12px helvetica")
    .attr("x", function(d) { return d.x; })
    .attr("y", function(d) { return d.y - 11; })
    .text(function(d) { return d.name; })
    .call(force.drag)

vis.style("opacity", 1e-6)
    .transition()
    .duration(1000)
    .style("opacity", 1)
    .style("align", "center")
    .style("border", 2);

force.on("tick", function() {
    path.attr("d", function(d) {
        var dx = d.target.x - d.source.x,
        dy = d.target.y - d.source.y,
        dr = 150/(d.key + 1);
        //mx = d.source.x + dx,
        //my = d.source.y + dy;
        //return ["M",d.source.x,d.source.y,"A",dr,dr,0,0,1,mx,my,"A",dr,dr,0,0,1,d.target.x,d.target.y].join(" ");
        return "M" + d.source.x + "," + d.source.y + "A" + dr + "," + dr + " 0 0,1 " + d.target.x + "," + d.target.y;

    });



    node.attr("transform", function (d) {
        return "translate(" + d.x + "," + d.y + ")";
    });

    text.attr("x", function(d) { return d.x; })
        .attr("y", function(d) { return d.y - 11 ; });
});

//Legend
var legend = vis.selectAll(".legend")
    .data(fill.domain())
    .enter().append("g")
    .attr("class", "legend")
    .attr("transform", function(d, i) { return "translate(0," + i * 20 + ")"; });

legend.append("g")
    .attr("cx", w - 32)
    .attr("cy", 8.5)
    .attr("r", 7.5);

legend.append("text")
    .attr("x", w - 44)
    .attr("y", 9)
    .attr("dy", ".35em")
    .style("text-anchor", "end")
    .text(function(d){return d});