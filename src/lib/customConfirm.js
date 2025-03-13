export function custom_confirm(message) {
    return new Promise((resolve) => {
        console.log("custom_confirm called");
        // Create modal elements
        const overlay = document.createElement("div");
        overlay.className = "custom-confirm-overlay";

        const confirmBox = document.createElement("div");
        confirmBox.className = "custom-confirm-box";

        const text = document.createElement("p");
        text.innerText = message;

        const buttons = document.createElement("div");
        buttons.className = "custom-confirm-buttons";

        const yesButton = document.createElement("button");
        yesButton.innerText = "Yes";
        yesButton.className = "confirm-yes";
        yesButton.onclick = () => {
            document.body.removeChild(overlay);
            resolve(true);
        };

        const noButton = document.createElement("button");
        noButton.innerText = "No";
        noButton.className = "confirm-no";
        noButton.onclick = () => {
            document.body.removeChild(overlay);
            resolve(false);
        };

        buttons.appendChild(yesButton);
        buttons.appendChild(noButton);
        confirmBox.appendChild(text);
        confirmBox.appendChild(buttons);
        overlay.appendChild(confirmBox);
        document.body.appendChild(overlay);
    });
}
