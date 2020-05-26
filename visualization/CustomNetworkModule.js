var NetworkModule = function (svg_width, svg_height) {

    // Create the svg tag:
    var svg_tag = "<svg width='" + svg_width + "' height='" + svg_height + "' " +
        "style='border:1px dotted'></svg>";

    // Append svg to #elements:
    $("#elements")
        .append($(svg_tag)[0]);

    var svg = d3.select("svg"),
        width = +svg.attr("width"),
        height = +svg.attr("height"),
        g = svg.append("g")
            .attr("transform", "translate(" + width / 2 + "," + height / 2 + ") scale(1)");

    var tooltip = d3.select("body").append("div")
        .attr("class", "tooltip")
        .style("opacity", 0);


    svg.call(d3.zoom()
        .on("zoom", function () {
            g.attr("transform", d3.event.transform);
        }));

    svg.on("mousemove", fish);

    var fish = function() {
        fisheye.focus(d3.zoomTransform(g.node()).invert(d3.mouse(this)));
      nodes.each(function(d) { d.fisheye = fisheye(d); })
          .attr("cx", function(d) { return d.fisheye.x; })
          .attr("cy", function(d) { return d.fisheye.y; })
          .attr("r", function(d) { return d.fisheye.z * 4.5; });

      links.attr("x1", function(d) { return d.source.fisheye.x; })
          .attr("y1", function(d) { return d.source.fisheye.y; })
          .attr("x2", function(d) { return d.target.fisheye.x; })
          .attr("y2", function(d) { return d.target.fisheye.y; });
    };

    var graph = null;
    var simulation = null;
    var links = null;
    var nodes = null;
    var quadtree = null;
    var fisheye = null;
    var node_count = 0;
    var edge_count = 0;

    this.createGraph = function (data) {
        graph = JSON.parse(JSON.stringify(data));
        init_fisheye();
        if (graph.fisheye === 1){
            fisheye = d3.fisheye.circular()
            .radius(300)
            .distortion(1.5);
        }
        else {
            fisheye = d3.fisheye.circular()
            .radius(0)
            .distortion(0);
        }

        if (simulation == null)
            simulation = d3.forceSimulation(graph.nodes)
                .force("charge", d3.forceManyBody()
                    .strength(-80)
                    .distanceMin(6))
                .force("link", d3.forceLink(graph.edges))
                .force("center", d3.forceCenter());
        // .stop();

        if (graph.interactive === 0){
            simulation.stop();
            for (var i = 0, n = Math.ceil(Math.log(simulation.alphaMin()) / Math.log(1 - simulation.alphaDecay())); i < n; ++i) {
                    simulation.tick();
                }
        }

        this.add_edges(graph.edges);
        this.add_nodes(graph.nodes);

        if (graph.interactive === 1)
            nodes.call(drag(simulation));


        simulation.on("tick", () => {
            nodes.each(function(d) { d.fisheye = fisheye(d); })
          .attr("cx", function(d) { return d.fisheye.x; })
          .attr("cy", function(d) { return d.fisheye.y; });

          links.attr("x1", function(d) { return d.source.fisheye.x; })
              .attr("y1", function(d) { return d.source.fisheye.y; })
              .attr("x2", function(d) { return d.target.fisheye.x; })
              .attr("y2", function(d) { return d.target.fisheye.y; });
            });


    };

    this.add_edges = function(e){
        let t;
        if (links){
            t = g.select("#glinks");
        }
        else{
            t = g.append("g").attr("id", "glinks");
        }
        links = t
            .selectAll("line")
            .data(e)
            .join("line")
            .attr("x1", function (d) { return d.source.x;})
            .attr("y1", function (d) { return d.source.y;})
            .attr("x2", function (d) { return d.target.x;})
            .attr("y2", function (d) { return d.target.y;})
            .attr("stroke-width", function (d) { return d.width; })
            .attr("line-id", function (d) { return d.id;})
            .attr("stroke", function (d) { return d.color;});
    };

    this.add_nodes = function(n){
        let t;
        if (nodes){
            t = g.select("#gnodes");
        }
        else{
            t = g.append("g").attr("id", "gnodes");
        }
        nodes = t
            .selectAll("circle")
            .data(n)
            .join("circle")
            .attr("cx", function (d) { return d.x;})
            .attr("cy", function (d) { return d.y;})
            .attr("r", function (d) { return d.size;})
            .attr("fill", function (d) { return d.color;})
            .attr("node-id", function (d) { return d.id;})
            .on("mouseover", function (d) {
                tooltip.transition()
                    .duration(200)
                    .style("opacity", .9);
                tooltip.html(d.tooltip)
                    .style("left", (d3.event.pageX) + "px")
                    .style("top", (d3.event.pageY) + "px");
            })
            .on("mouseout", function () {
                tooltip.transition()
                    .duration(500)
                    .style("opacity", 0);
            });
    };
    
    this.render = function (data) {
        let i;
        var current_graph = JSON.parse(JSON.stringify(data));
        if (graph == null) {
            this.createGraph(data);
        }
        else if (node_count < current_graph.nodes.length){
            var existing_nodes = simulation.nodes();
            for(var j = 0; j < existing_nodes.length;j++){
                existing_nodes[j]['tooltip'] = current_graph.nodes[j].tooltip;
                existing_nodes[j]['color'] = current_graph.nodes[j].color;
                current_graph.nodes[j] = existing_nodes[j];
                // current_graph.nodes[j]['index'] = existing_nodes[j].index;
                // current_graph.nodes[j]['x'] = existing_nodes[j].x;
                // current_graph.nodes[j]['y'] = existing_nodes[j].y;
                // current_graph.nodes[j]['vx'] = existing_nodes[j].vx;
                // current_graph.nodes[j]['vy'] = existing_nodes[j].vy;
            }
            // console.log(current_graph.nodes);
            simulation.nodes(current_graph.nodes);
            simulation.force("link").links(current_graph.edges);
            simulation.alpha(0.1).restart();

            this.add_edges(current_graph.edges);
            this.add_nodes(current_graph.nodes);

            simulation.on("tick", () => {
                nodes.each(function(d) { d.fisheye = fisheye(d); })
                    .attr("cx", function(d) { return d.fisheye.x; })
                    .attr("cy", function(d) { return d.fisheye.y; });

            links.attr("x1", function(d) { return d.source.fisheye.x; })
                .attr("y1", function(d) { return d.source.fisheye.y; })
                .attr("x2", function(d) { return d.target.fisheye.x; })
                .attr("y2", function(d) { return d.target.fisheye.y; });
            });
        }
        node_count = current_graph.nodes.length;
        edge_count = current_graph.edges.length;

        g.selectAll("line")
            .attr("stroke",function (d, i) { return  current_graph.edges[i].color });
        g.selectAll("circle")
            .attr("fill",function (d, i) { return current_graph.nodes[i].color });

    };

    drag = simulation => {

        function dragstarted(d) {
            if (!d3.event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }

        function dragged(d) {
            d.fx = d3.event.x;
            d.fy = d3.event.y;
        }

        function dragended(d) {
            if (!d3.event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }

        // function subject(d) {
        //     if (quadtree == null){
        //         quadtree = d3.quadtree().x(d => d.cx).y(d => d.cy).addAll(nodes);
        //     }
        //     return quadtree.find(d3.event.x, d3.event.y, 5)
        // }

        return d3.drag()
            // .subject(subject)
            .on("start", dragstarted)
            .on("drag", dragged)
            .on("end", dragended);
    };

    this.reset = function () {
        graph = null;
        simulation = null;
        links = null;
        nodes = null;
        quadtree = null;
        fisheye = null;
        node_count = 0;
        edge_count = 0;

        svg.selectAll("g")
            .remove();
        g = svg.append("g")
            .attr("transform", "translate(" + width / 2 + "," + height / 2 + ")");

        svg.call(d3.zoom()
            .on("zoom", function () {
                g.attr("transform", d3.event.transform);
            }));

        svg.on("mousemove", fish);
    }
};