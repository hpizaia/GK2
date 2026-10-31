/* GK.ui.toast(msg): the transient status message at the bottom (#toast). Owns that element.
*/
GK.ui.toast = (function () {
  let timer = null;
  return function toast(msg) {
    const el = document.getElementById("toast");
    el.textContent = msg; el.hidden = false;
    clearTimeout(timer);
    timer = setTimeout(() => { el.hidden = true; }, 2200);
  };
})();
