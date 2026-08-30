// Loaded first, in <head>, before the stylesheet -- sets data-theme from the
// saved preference (if any) so the correct palette paints on first frame
// instead of flashing the system-default theme and then switching.
(function () {
  try {
    var saved = localStorage.getItem("dsme_theme");
    if (saved === "light" || saved === "dark") {
      document.documentElement.setAttribute("data-theme", saved);
    }
  } catch (e) {
    // localStorage unavailable (private mode etc.) -- fall back to system preference.
  }
})();
