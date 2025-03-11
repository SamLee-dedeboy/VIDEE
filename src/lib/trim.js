export function trim(node) {
    node.addEventListener("input", (event) => {
        // trimBr(event.target);
        if (event.target.innerHTML === "<br>") {
            event.target.innerHTML = "";
          }
      });
}
function trimBr(element) {
    while (element.firstChild && element.firstChild.nodeName === "BR") {
      element.removeChild(element.firstChild);
    }
    while (element.lastChild && element.lastChild.nodeName === "BR") {
      element.removeChild(element.lastChild);
    }
  }