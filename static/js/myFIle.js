document.getElementById('demo').innerHTML = 'Created with JS'

document.addEventListener('DOMContentLoaded', function() {
    const disabledButton = document.querySelector('.disabled-download');
    
    if (disabledButton) {
        disabledButton.addEventListener('click', function(event) {
            event.preventDefault(); // Prevent any default action
            // Check if the button is disabled
            if (disabledButton.classList.contains('disabled-download')) {
                // Show the message, you can replace 'alert' with a more custom method like inserting an error into the DOM.
                alert('You need to be logged in to download the data.');
            }
        });
    }
});