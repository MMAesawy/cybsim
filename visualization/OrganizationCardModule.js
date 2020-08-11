class OrganizationCardModule{

    static moduleCount = 0;
    static properties = {
        ORG_CARD_WIDTH: 200,
        ORG_CARD_HEIGHT: 200,
        ORG_CARD_RECT_ROUND_X: 10,
        ORG_CARD_RECT_ROUND_Y: 10,
        ID_TEXT_POS_X: 100,
        ID_TEXT_POS_Y: 187.5,
        SEC_TEXT_POS_X: 40,
        SEC_TEXT_POS_Y: 180,
        SEC_LABEL_POS_X: 40,
        SEC_LABEL_POS_Y: 195,
        UTIL_TEXT_POS_X: 160,
        UTIL_TEXT_POS_Y: 180,
        UTIL_LABEL_POS_X: 160,
        UTIL_LABEL_POS_Y: 195,
        TOP_SEPARATOR_HEIGHT: 140,
        BOTTOM_SEPARATOR_HEIGHT: 160,
        COMP_ARC_OUTER_RADIUS: 19,
        COMP_ARC_INNER_RADIUS: 14,
        COMP_ARC_POS_X: 100,
        COMP_ARC_POS_Y: 180,
        Y_AXIS_START: 25,
        BARGRAPH_TOP_MARGIN: 15,
        BARGRAPH_SIDE_MARGIN: 4,
        GRIDLINE_OPACITY: "15%",

        EFFECTIVENESS_BAR_OPACITY: "10%",
        LINKS_BASE_OPACITY: 0.05,
        LINKS_STROKE_MIN: 1,
        LINKS_STROKE_MAX: 4,
    };

    constructor(svg_width, svg_height){


        this.id = 'ocm-' + OrganizationCardModule.moduleCount;
        OrganizationCardModule.moduleCount++;
        this.svg_tag = "<svg width='" + svg_width + "' height='" + svg_height + "' " +
        "style='border:1px dotted' id='" + this.id + "'></svg>";


        // Append svg to #elements:
        $("#elements")
            .append($(this.svg_tag)[0]);

        this.canvas = d3.select("#" + this.id);
        this.g = this.canvas.append("g")
            .attr("id", "base")
            .attr("transform", "translate(" + svg_width / 2 + "," + svg_height / 2 + ") scale(1)");

        this.canvas.call(d3.zoom()
            .on("zoom", function () {
                this.g.attr("transform", d3.event.transform);
            }.bind(this)));

        this.reset();

        // maybe tie to CSS using classes instead of colors?
        this.color = d3.scaleOrdinal(["bar-graph-attack", "bar-graph-information"]);
        this.keys = ["frac_comp", "frac_info"];
        // this.keys = ["0", "1"]; // keys screw up for some reason
    }

    orgEnter(newGroups, orgData){
        //console.log(newGroups.size());
        if (!newGroups.size()) return;
        //console.log("Entering...");
        let cardLayers = newGroups.append("svg")
            .attr("class", "orgcard")
            .attr("id", function(d) { return d.id; })
            .attr("overflow", "visible")
            .attr("width", OrganizationCardModule.properties.ORG_CARD_WIDTH)
            .attr("height", OrganizationCardModule.properties.ORG_CARD_HEIGHT);


        // add rectangles
        cardLayers.append("rect")
            .attr("class", "cardbox")
            .attr("rx", OrganizationCardModule.properties.ORG_CARD_RECT_ROUND_X)
            .attr("ry", OrganizationCardModule.properties.ORG_CARD_RECT_ROUND_Y)
            // .attr("x", function(){ return this.g.x; }.bind(this))
            // .attr("y", function(){ return this.g.y; }.bind(this))
            .attr("width", OrganizationCardModule.properties.ORG_CARD_WIDTH)
            .attr("height", OrganizationCardModule.properties.ORG_CARD_HEIGHT);

        // add id pie chart
        cardLayers.append("path")
            .attr("class", "arc")
            .attr("d",
                function(d) { return d3.arc()
                                        .innerRadius(OrganizationCardModule.properties.COMP_ARC_INNER_RADIUS)
                                        .outerRadius(OrganizationCardModule.properties.COMP_ARC_OUTER_RADIUS)
                                        .startAngle(0)
                                        .endAngle(Math.PI * 2 * (d.frac_compromised*0.999+0.001))();
                    })
            .attr("transform", "translate(" + OrganizationCardModule.properties.COMP_ARC_POS_X
                + "," + OrganizationCardModule.properties.COMP_ARC_POS_Y + ")");

        // add id pie chart outline
        cardLayers.append("path")
            .attr("class", "arc-outline")
            .attr("d",
                function(d) { return d3.arc()
                                        .innerRadius(OrganizationCardModule.properties.COMP_ARC_INNER_RADIUS)
                                        .outerRadius(OrganizationCardModule.properties.COMP_ARC_OUTER_RADIUS)
                                        .startAngle(0)
                                        .endAngle(Math.PI * 2)();
                    })
            .attr("transform", "translate(" + OrganizationCardModule.properties.COMP_ARC_POS_X
                + "," + OrganizationCardModule.properties.COMP_ARC_POS_Y + ")");

        // add id text
        cardLayers.append("text")
            .attr("class", "cardtext idlabel")
            .attr("dx", OrganizationCardModule.properties.ID_TEXT_POS_X)
            .attr("dy", OrganizationCardModule.properties.ID_TEXT_POS_Y)
            .text(function(d) { return d.id; });

        // add security text
        cardLayers.append("text")
            .attr("class", "cardtext securitytext")
            .attr("dx", OrganizationCardModule.properties.SEC_TEXT_POS_X)
            .attr("dy", OrganizationCardModule.properties.SEC_TEXT_POS_Y)
            .text(function(d) { return d.sec_bud.toFixed(3); });

        // add security label
        cardLayers.append("text")
            .attr("class", "cardtext securitylabel")
            .attr("dx", OrganizationCardModule.properties.SEC_LABEL_POS_X)
            .attr("dy", OrganizationCardModule.properties.SEC_LABEL_POS_Y)
            .text("Security");

        // add utility text
        cardLayers.append("text")
            .attr("class", "cardtext utilitytext")
            .attr("dx", OrganizationCardModule.properties.UTIL_TEXT_POS_X)
            .attr("dy", OrganizationCardModule.properties.UTIL_TEXT_POS_Y)
            .text(function(d) { return d.utility.toFixed(3); });

        // add utility label
        cardLayers.append("text")
            .attr("class", "cardtext utilitylabel")
            .attr("dx", OrganizationCardModule.properties.UTIL_LABEL_POS_X)
            .attr("dy", OrganizationCardModule.properties.UTIL_LABEL_POS_Y)
            .text("Freeloading");

        // add `E` label
        // lots of magic numbers and inappropriate classes here, but it works for now and nobody will change this anyways
        cardLayers.append("text")
            .attr("class", "cardtext utilitylabel")
            .attr("dx", 12.5)
            .attr("dy",OrganizationCardModule.properties.BOTTOM_SEPARATOR_HEIGHT
                + (OrganizationCardModule.properties.TOP_SEPARATOR_HEIGHT
                    - OrganizationCardModule.properties.BOTTOM_SEPARATOR_HEIGHT)/2 + 4)
            .text("E");

        // add bottom bar graph layer
        cardLayers.append("g")
            .attr("class", "bottomBarGraph");

        // add effectiveness bar graph layer
        cardLayers.append("g")
            .attr("class", "effectBarGraph");

        // add y axis
        this.yAxis = cardLayers.append("g")
            .attr("class", "yAxis")
            .attr("transform", `translate(${OrganizationCardModule.properties.Y_AXIS_START},0)`)
            .call(d3.axisLeft(this.y)
                // .ticks(null, "s"))
                .tickValues([".1",".2",".3",".4",".5",".6",".7",".8",".9", "1.0"])
                .tickFormat(d3.format(".1f"))
                .tickSize(4)
            )
            .call(g => g.select(".domain").remove())
            .call(g => g.select(".tick:last-of-type text").clone()
                .attr("x", 2)
                .attr("y", -8)
                .attr("text-anchor", "start")
                .attr("font-weight", "bold")
                .attr("font-size", "10px")
                .text("%"));

        // add gridlines
        this.cardLayer.selectAll("g.tick")
            .append("line")
            //.attr("class", "gridline") // CSS does not get applied on ticks for some unknown reason
            .attr("stroke", "currentColor")
            .attr("opacity", OrganizationCardModule.properties.GRIDLINE_OPACITY)
            .attr("x2", OrganizationCardModule.properties.ORG_CARD_WIDTH);

        // add x axis
        this.xAxis = cardLayers.append("g")
            .attr("class", "xAxis")
            .attr("transform", `translate(0,${OrganizationCardModule.properties.TOP_SEPARATOR_HEIGHT})`)
            .call(d3.axisBottom(this.x0)
                .tickSizeOuter(0)
                .tickFormat(d => "A" + d3.format("~r")(d))
            )
            .call(g => g.select(".domain").remove());

        let lineLayer = cardLayers.append("g");

        // add top separator line
        lineLayer.append("line")
            .attr("class", "cardline")
            .attr("x1", 0)
            .attr("y1", OrganizationCardModule.properties.TOP_SEPARATOR_HEIGHT)
            .attr("x2",OrganizationCardModule.properties.ORG_CARD_WIDTH)
            .attr("y2",OrganizationCardModule.properties.TOP_SEPARATOR_HEIGHT);

        // add left separator line
        lineLayer.append("line")
            .attr("class", "cardline")
            .attr("x1", OrganizationCardModule.properties.Y_AXIS_START)
            .attr("y1", 0)
            .attr("x2",OrganizationCardModule.properties.Y_AXIS_START)
            .attr("y2",OrganizationCardModule.properties.BOTTOM_SEPARATOR_HEIGHT);

        // add bottom separator line
        lineLayer.append("line")
            .attr("class", "cardlinemajor")
            .attr("x1", 0)
            .attr("y1", OrganizationCardModule.properties.BOTTOM_SEPARATOR_HEIGHT)
            .attr("x2",OrganizationCardModule.properties.ORG_CARD_WIDTH)
            .attr("y2",OrganizationCardModule.properties.BOTTOM_SEPARATOR_HEIGHT);


        // ========== COMMENT OUT TO DISABLE LINK RENDERING ========
        let links = this.linkLayer.selectAll("line")
            .data(this.nodeLinks)
            .join("line")
            // .attr("class", "graphlink")
            .attr("stroke", "black")
            .attr("stroke-width", OrganizationCardModule.properties.LINKS_STROKE_MIN);
        // =========================================================

        if (this.simulation == null){
            this.simulation = d3.forceSimulation(this.nodes)
               // .alphaTarget(0.1)
                .force("center", d3.forceCenter())
                .force("link", d3.forceLink(this.nodeLinks)
                    .distance(function (d) { return 1000; })
                    .strength(0.1))
                .force("collision", d3.forceCollide(150));
            // .force("charge", d3.forceManyBody()
            //             .strength(500)
            //             .distanceMin(300));
            for (let i = 0; i < 100; i++)
                this.simulation.tick();
        }

        /* ============== enable dragging ==============*/
        cardLayers.call(d3.drag()
            // .subject(subject)
            .on("start", function(d) {
                if (!d3.event.active)
                    this.simulation.alphaTarget(0.3).restart();
                d.fx = d.x;
                d.fy = d.y;
            }.bind(this))
            .on("drag", function(d) {
                d.fx = d3.event.x;
                d.fy = d3.event.y;
            }.bind(this))
            .on("end", function(d) {
                if (!d3.event.active)
                    this.simulation.alphaTarget(0);
                d.fx = null;
                d.fy = null;
            }.bind(this)));

        this.simulation.on("tick", () => {
            cardLayers
                .attr("x", function(d) { return d.x-OrganizationCardModule.properties.ORG_CARD_WIDTH/2; })
                .attr("y", function(d) { return d.y-OrganizationCardModule.properties.ORG_CARD_HEIGHT/2; });

            // ========== COMMENT OUT TO DISABLE LINK RENDERING =============
            links
                .attr("x1", function(d) { return d.source.x; })
                .attr("x2", function(d) { return d.target.x; })
                .attr("y1", function(d) { return d.source.y; })
                .attr("y2", function(d) { return d.target.y; })
            // ==============================================================
        });
    }

    render(data){
        let orgData = JSON.parse(JSON.stringify(data));

        if (orgData["num_attackers"] > this.numAttackers){
            this.numAttackers = orgData["num_attackers"];
            this.x0 = d3.scaleBand()
                    .domain(this.consecutiveArrayFactory(this.numAttackers))
                    .rangeRound([
                        OrganizationCardModule.properties.Y_AXIS_START
                        + OrganizationCardModule.properties.BARGRAPH_SIDE_MARGIN,
                        OrganizationCardModule.properties.ORG_CARD_WIDTH
                        - OrganizationCardModule.properties.BARGRAPH_SIDE_MARGIN
                    ])
                    .paddingInner(0.1);
            this.x1 = d3.scaleBand()
                        .domain(this.keys)
                        .rangeRound([0, this.x0.bandwidth()])
                        .padding(0.05);
            this.y = d3.scaleLinear()
                        .domain([0, 1])
                        .rangeRound([
                            OrganizationCardModule.properties.TOP_SEPARATOR_HEIGHT,
                            OrganizationCardModule.properties.BARGRAPH_TOP_MARGIN
                        ]);
            this.y2 = d3.scaleLinear()
                        .domain([0, 1])
                        .rangeRound([
                            OrganizationCardModule.properties.BOTTOM_SEPARATOR_HEIGHT,
                            OrganizationCardModule.properties.TOP_SEPARATOR_HEIGHT
                        ]);
            if (this.xAxis)
                this.xAxis
                    .transition()
                    .call(d3.axisBottom(this.x0)
                    .tickSizeOuter(0)
                    .tickFormat(d => "A" + d3.format("~r")(d))
                )
                .call(g => g.select(".domain").remove());
        }

        // create new links
        while (this.nodeCount < orgData.nodes.length){
            for (let i = this.nodeCount - 1; i >= 0; i--) {
                this.nodeLinks.push({
                    // 'source': orgData.nodes[this.nodeCount].id,
                    // 'target': orgData.nodes[i].id});
                    'source': this.nodeCount,
                    'target': i});
            }
            this.nodes.push(orgData.nodes[this.nodeCount]);
            this.nodeCount++;
        }
        // assign data to new nodes?
        for (let i = 0; i < this.nodeCount; i++){
            Object.assign(this.nodes[i], orgData.nodes[i]);
        }
        // for (let attrname in orgData.nodes) { this.nodes[attrname] = orgData.nodes[attrname]; }
        let cards = this.cardLayer.selectAll("svg").data(this.nodes);

        this.orgEnter(cards.enter(), orgData);
        //cards.exit().remove();

        /* ===================== UPDATES ===================== */

        cards
            .select("text.securitytext")
            .text(function(d) { return d.sec_bud.toFixed(3); });
        cards
            .select("text.utilitytext")
            .text(function(d) { return d.utility.toFixed(3); });
        cards
            .select("path.arc")
            // .transition()
            .attr("d",
                function(d) {
                return d3.arc()
                        .innerRadius(OrganizationCardModule.properties.COMP_ARC_INNER_RADIUS)
                        .outerRadius(OrganizationCardModule.properties.COMP_ARC_OUTER_RADIUS)
                        .startAngle(0)
                        .endAngle(Math.PI * 2 * (d.frac_compromised*0.999+0.001))();
                    });

        //update link opacity
        this.linkLayer.selectAll("line")
            .data(data.closeness)
            //.attr("debug", d => console.log(d))
            .attr("stroke-width", d => (OrganizationCardModule.properties.LINKS_STROKE_MIN
                                                        + d.value
                                                        * (OrganizationCardModule.properties.LINKS_STROKE_MAX
                                                            - OrganizationCardModule.properties.LINKS_STROKE_MIN))
                                                        + "")
            .attr("opacity", d => ((d.value
                                                *(1-OrganizationCardModule.properties.LINKS_BASE_OPACITY)
                                                + OrganizationCardModule.properties.LINKS_BASE_OPACITY)*100) + "%");

        // add and update bottom bar graph
        this.cardLayer
            .selectAll("svg")
            .select("g.bottomBarGraph") // one g for each org svg
            .data(this.nodes.map(d => d.attack_data)) // extract `attack_data` from each org data. n = org_count
            .join("g")
            .attr("class", "bottomBarGraph")
            .selectAll("g") // one grouping for each `attack_data` object
            .data(d=>d) // same data, new join
            .join("g")
            .attr("transform", (d, i) => `translate(${this.x0(i+1)},0)`) // move grouping to margin start
            //.attr("debug", d=>console.log(d))       // if you're lost, try enabling these debug attr to view data
            .selectAll("rect") // select rect for each item. this is very confusing and i just wrote this code myself.
            .data(d => this.keys.map(key => ({key, value: d[key]*0.999+0.001}))) // transform each object to key-value pair
            .join("rect")
            .transition()
            //.attr("debug", d=>console.log(d))
            .attr("x", d => this.x1(d.key))
            .attr("y", d => this.y(d.value))
            .attr("width", this.x1.bandwidth())
            .attr("height", d => this.y(0) - this.y(d.value))
            .attr("class", d => this.color(d.key));

        // ====================== COMMENT OUT TO REMOVE EFFECTIVENESS GRAPH ===================================
        // add and update effectiveness bar graph
        this.cardLayer
            .selectAll("svg")
            .select("g.effectBarGraph") // one g for each org svg
            //.attr("transform", (d, i) => `translate(${this.x0(i+1)},0)`) // move grouping to margin start
            //.attr("debug", d=>console.log(d))       // if you're lost, try enabling these debug attr to view data
            .selectAll("rect")
            .data(data.attack_effectiveness.map(d => d*0.999+0.001))
            .join("rect")
            .transition()
            // .attr("debug", d=>console.log(d))
            .attr("x", (d, i) => this.x0(i+1))
            .attr("y", d => this.y2(d))
            .attr("width", this.x0.bandwidth())
            .attr("height", d => this.y2(0) - this.y2(d))
            .attr("class", "bar-graph-attack")
            .attr("opacity", OrganizationCardModule.properties.EFFECTIVENESS_BAR_OPACITY);
        // ====================================================================================================


        // update links
        this.simulation
            .alpha(0.05).restart() // alpha value determines how "jarring" the closeness updates are.
            .force("link", d3.forceLink(data.closeness)
            .distance(function (d) { return 1000 * (1 -  d.value); })
            .strength(1.0));

        /* ================================================= */

    }

    reset(){
        this.simulation = null;
        this.nodeLinks = [];
        this.nodes = [];
        this.nodeCount = 0;

        this.x0 = null;
        this.x1 = null;
        this.y = null;
        this.y2 = null;
        this.yAxis = null;
        this.xAxis = null;
        this.numAttackers = 0;

        this.g.selectAll("g").remove();

        this.linkLayer = this.g.append("g");
        this.cardLayer = this.g.append("g");
    }

    consecutiveArrayFactory(num){
        let a = [];
        for (let i = 1; i <= num; i++)
            a.push("" + i);
        return a;
    }






        // function subject(d) {
        //     if (quadtree == null){
        //         quadtree = d3.quadtree().x(d => d.cx).y(d => d.cy).addAll(nodes);
        //     }
        //     return quadtree.find(d3.event.x, d3.event.y, 5)
        // }





}