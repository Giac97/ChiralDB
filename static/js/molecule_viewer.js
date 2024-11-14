document.addEventListener('DOMContentLoaded', function() {
    // Get the PubChem Compound ID from a data attribute on the container
    const container = document.querySelector('#container-01');
    const cid = container.dataset.cid;
    let viewer; // Declare viewer variable in the outer scope
    let isAnimating = false; // Animation state

    if (cid) {
        let config = { backgroundColor: 'white' };
        viewer = $3Dmol.createViewer(container, config);

        fetch(`https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/CID/${cid}/SDF?record_type=3d&response_type=save`)
            .then(response => response.text())
            .then(data => {
                viewer.addModel(data, 'sdf'); // Load the molecule into the viewer

                // Set ball-and-stick style

                // Set sphere style with a smaller scale
                viewer.setStyle({}, {  stick: {radius: 0.1, doubleBondScaling : 0.8,color: 'spectrum'}, sphere: { scale: 0.3,color: 'spectrum' } }); 

                viewer.setBackgroundColor('white'); // Ensure background is white
                viewer.zoomTo(); // Zoom to the molecule
                viewer.render(); // Render the viewer
                viewer.zoom(0.8, 2000); // Apply zoom
            })
            .catch(error => console.error('Error fetching data from PubChem:', error));
    }

    // Function to animate the model around the Z-axis
    function animateModel() {
        if (!isAnimating) return; // If not animating, exit the function

        viewer.rotate(0, 0, 0.1); // Rotate around the Z-axis
        viewer.render(); // Render the updated model
        requestAnimationFrame(animateModel); // Continue animating
    }

    // Button event listener
    const animateButton = document.getElementById('animate-button');
    animateButton.addEventListener('click', function() {
        isAnimating = !isAnimating; // Toggle animation state
        if (isAnimating) {
            animateModel(); // Start the animation
        }
    });
});
