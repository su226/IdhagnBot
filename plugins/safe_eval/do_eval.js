const posix = require("posix");
let chunks = [];

process.stdin.on("data", chunk => {
  chunks.push(chunk);
});

/** @interface */ class EvalData {
  /** @type {string} */ code;
  /** @type {number} */ nproc;
  /** @type {number} */ memory;
}

process.stdin.on("end", () => {
  /** @type {EvalData} */
  const data = JSON.parse(chunks.join());
  posix.setrlimit("as", {soft: data.memory, hard: data.memory});
  posix.setrlimit("nproc", {soft: data.nproc, hard: data.nproc});
  eval(data.code);
});
