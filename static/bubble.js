// Embed the data directly into JavaScript (expanded to 10 nodes for demonstration)
// URL for fetching data (replace with your actual URL)

// Sample data as a fallback (in case fetch fails)
// Function to initialize the visualization with the data
function initializeVisualization(data) {
  // Display the token info as a title
  const title = `${data.full_name} (${data.symbol}) on ${data.chain.toUpperCase()} - Updated: ${data.dt_update}`;
  document.getElementById("title").textContent = title;

  // Prepare the data for D3.js
  data.nodes.forEach((node) => {
    node.id = node.address;
  });

  // Transform the links: map source and target indices to node objects
  const links = data.links
    .map((link) => {
      const sourceNode = data.nodes[link.source];
      const targetNode = data.nodes[link.target];
      if (!sourceNode || !targetNode) {
        console.warn("Invalid link:", link);
        return null;
      }
      return {
        source: sourceNode,
        target: targetNode,
        value: Math.max(link.forward, link.backward),
        forward: link.forward,
        backward: link.backward,
        direction: link.forward >= link.backward ? "forward" : "backward",
      };
    })
    .filter((link) => link !== null);

  // Set up the SVG canvas
  const svg = d3.select("svg");
  const width = svg.node().getBoundingClientRect().width; // Get the actual pixel width
  const height = +svg.attr("height");

  // Define a scale for the radius (based on amount)
  const radiusScale = d3
    .scaleSqrt()
    .domain([0, d3.max(data.nodes, (d) => d.amount)])
    .range([10, 90]); // Reduced max radius for more nodes

  // Define a scale for the line thickness (based on link value)
  const linkScale = d3
    .scaleLinear()
    .domain([0, d3.max(links, (d) => d.value)])
    .range([1, 10]); // Reduced max thickness for clarity

  // Define the arrowhead marker
  svg
    .append("defs")
    .append("marker")
    .attr("id", "arrow")
    .attr("viewBox", "0 -5 10 10")
    .attr("refX", 15)
    .attr("refY", 0)
    .attr("markerWidth", 10)
    .attr("markerHeight", 10)
    .attr("orient", "auto")
    .append("path")
    .attr("d", "M0,-5L10,0L0,5")
    .attr("class", "arrow");

  // Create a force simulation with parameters for circular arrangement
  const simulation = d3
    .forceSimulation(data.nodes)
    .force("link", d3.forceLink(links).distance(200)) // Short distance for tight clustering
    .force("charge", d3.forceManyBody().strength(-100)) // Strong repulsion for circular spread
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force(
      "collide",
      d3.forceCollide((d) => radiusScale(d.amount) + 10),
    );

  // Draw nodes (bubbles)
  const node = svg
    .append("g")
    .attr("class", "nodes")
    .selectAll("circle")
    .data(data.nodes)
    .enter()
    .append("circle")
    .attr("class", "node")
    .attr("r", (d) => radiusScale(d.amount))
    .call(
      d3
        .drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended),
    );

  // Draw links (lines between nodes) with arrows and variable thickness
  const link = svg
    .append("g")
    .attr("class", "links")
    .selectAll("line")
    .data(links)
    .enter()
    .append("line")
    .attr("class", "link")
    .attr("marker-end", (d) =>
      d.direction === "forward" ? "url(#arrow)" : "url(#arrow)",
    );

  // Initialize node positions roughly for immediate zoom
  data.nodes.forEach((node, i) => {
    node.x = node.x || width / 2 + Math.cos(i) * 100;
    node.y = node.y || height / 2 + Math.sin(i) * 100;
  });

  // Apply the default zoom immediately
  fitGraph();

  // Update positions on each tick of the simulation
  simulation.on("tick", () => {
    link
      .attr("x1", (d) => d.source.x)
      .attr("y1", (d) => d.source.y)
      .attr("x2", (d) => d.target.x)
      .attr("y2", (d) => d.target.y);

    node.attr("cx", (d) => d.x).attr("cy", (d) => d.y);
  });

  // Drag functions
  function dragstarted(event, d) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
  }

  function dragged(event, d) {
    d.fx = event.x;
    d.fy = event.y;
  }

  function dragended(event, d) {
    if (!event.active) simulation.alphaTarget(0);
    d.fx = null;
    d.fy = null;
  }

  // Add zoom functionality
  const zoom = d3
    .zoom()
    .extent([
      [0, 0],
      [width, height],
    ])
    .scaleExtent([0.3, 8]) // Allow zooming out further if needed
    .on("zoom", zoomed);
  svg.call(zoom);

  function zoomed({ transform }) {
    svg.selectAll(".nodes").attr("transform", transform);
    svg.selectAll(".links").attr("transform", transform);
  }

  // Fit the graph to the view
  // Set a default zoom-out level
  function fitGraph() {
    // Compute the bounding box of the nodes
    const bounds = {
      xMin: Infinity,
      xMax: -Infinity,
      yMin: Infinity,
      yMax: -Infinity,
    };
    data.nodes.forEach((node) => {
      if (node.x && node.y) {
        // Ensure node positions are defined
        bounds.xMin = Math.min(bounds.xMin, node.x);
        bounds.xMax = Math.max(bounds.xMax, node.x);
        bounds.yMin = Math.min(bounds.yMin, node.y);
        bounds.yMax = Math.max(bounds.yMax, node.y);
      }
    });

    // Add padding and compute the scale
    const padding = 50;
    const graphWidth = bounds.xMax - bounds.xMin;
    const graphHeight = bounds.yMax - bounds.yMin;
    const scaleX = (width - 2 * padding) / graphWidth;
    const scaleY = (height - 2 * padding) / graphHeight;
    let scale = Math.min(scaleX, scaleY, 1);

    // Enforce a default zoom-out level (e.g., at least 50% zoom)
    const defaultZoomScale = 1.5; // percentage
    scale = Math.min(scale, defaultZoomScale);

    // Compute the translation to center the graph
    const translateX = (width - graphWidth * scale) / 2 - bounds.xMin * scale;
    const translateY = (height - graphHeight * scale) / 2 - bounds.yMin * scale;

    // Apply the zoom transform to the correct elements
    const transform = d3.zoomIdentity
      .translate(translateX, translateY)
      .scale(scale);
    svg.selectAll(".nodes").attr("transform", transform);
    svg.selectAll(".links").attr("transform", transform);

    // Update the zoom handler to reflect this transform
    // svg.call(zoom.transform, transform);
  }
  simulation.on("end", fitGraph);

  // Add tooltips with name and amount
  node.on("mouseover", function (event, d) {
    d3.select(this)
      .append("title")
      .text(`${d.name}: ${d.amount.toLocaleString()} ${data.symbol}`);
  });
}

// Fetch the data and initialize the visualization
initializeVisualization(data);
