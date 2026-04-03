import { createStore } from "/js/AlpineStore.js";

// Sidebar Bottom store manages version info display
const model = {
  versionNo: "",
  commitTime: "",

  get versionLabel() {
    if (this.versionNo && !this.commitTime) return this.versionNo;
    return this.versionNo && this.commitTime
      ? `Version ${this.versionNo} ${this.commitTime}`
      : "";
  },

  init() {
    // Load version info from global scope (exposed in index.html)
    const gi = globalThis.gitinfo;
    if (gi && gi.version) {
      this.versionNo = gi.version;
      this.commitTime = gi.commit_time || "";
    }
  },
};

export const store = createStore("sidebarBottom", model);

