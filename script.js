// WebSocket connection for real-time interaction
let socket;
let pdfContent = "";

// Initialize WebSocket connection
function connectWebSocket() {
    socket = new WebSocket("ws://localhost:8084/ws");
    socket.onopen = function () {
        console.log("WebSocket connection established.");
    };

    socket.onmessage = function (event) {
        const message = event.data;
        const chatMessages = document.getElementById("chat-box");
        const messageDiv = document.createElement("div");
        messageDiv.classList.add("bot-message"); // Add the bot message style
        messageDiv.textContent = message;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight; // Auto-scroll to the latest message
    };

    socket.onclose = function () {
        console.log("WebSocket connection closed.");
    };
}

// Send user input to the server
function sendMessage() {
    const userInput = document.getElementById("user-input").value;
    if (userInput) {
        const chatMessages = document.getElementById("chat-box");

        // Create a div for the user's message
        const messageDiv = document.createElement("div");
        messageDiv.classList.add("user-message"); // Add the user message style
        messageDiv.textContent = userInput;
        chatMessages.appendChild(messageDiv);

        chatMessages.scrollTop = chatMessages.scrollHeight; // Auto-scroll to the latest message

        socket.send(userInput); // Send message to WebSocket
        document.getElementById("user-input").value = ""; // Clear input field
    }
}

// Handle PDF file upload
function uploadPDF() {
    const fileInput = document.getElementById("pdf-upload");
    const file = fileInput.files[0];
    if (file) {
        const formData = new FormData();
        formData.append("file", file);

        fetch("/upload", {
            method: "POST",
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.message === "PDF uploaded and content extracted successfully.") {
                alert("PDF uploaded successfully!");
                connectWebSocket(); // Start WebSocket after upload
            } else {
                alert("Error uploading PDF.");
            }
        })
        .catch(error => {
            console.error("Error uploading PDF:", error);
            alert("Error uploading PDF.");
        });
    } else {
        alert("Please select a PDF file first.");
    }
}

// Toggle settings modal visibility
function toggleSettingsModal() {
    const modal = document.getElementById("settings-modal");
    modal.classList.toggle("visible");
}

// Add event listener for the Enter key to send the message
document.getElementById("user-input").addEventListener("keydown", function (event) {
    if (event.key === "Enter") { // Check if the Enter key is pressed
        event.preventDefault(); // Prevent default form submission (if any)
        sendMessage(); // Call the sendMessage function
    }
});

// Event listener to ensure WebSocket is connected when the page loads
document.addEventListener("DOMContentLoaded", function() {
    connectWebSocket();
});