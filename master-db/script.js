const WORKER = new Worker("worker.js")

const partProgress = document.getElementById("tl-progress-part");
const dataProgress = document.getElementById("tl-progress");

WORKER.onmessage = function ({ data: { action, payload } }) {
    if (window[action]) {
        window[action](payload);
    }
}

// savedb exports the db as a downloadable file to the user
function saveDB(blobUrl) {
    const a = document.createElement('a')
    a.href = blobUrl
    a.download = "master.mdb"
    a.click()
    setTimeout(() => window.URL.revokeObjectURL(blobUrl), 1000)
    log({name: "create_db", create_type: "finished"})
};

function process() {
    dataProgress.value += 1;
};

function translate({ parts, dataMax }) {
    partProgress.textContent = parts;
    dataProgress.max = dataMax;
    dataProgress.value = 0;
    document.getElementById("tl-prog-cont").style.visibility = "visible";
};

function listenFileChange() {
    const dbFileEl = document.getElementById("dbfile");
    function getOvr() {
        return Array.prototype.reduce.call(document.querySelectorAll("#overrides input:checked"), (o, v) => { o[v.name] = v.value; return o}, {});
    }

    dbFileEl.addEventListener("change", () => {
        //* msg
        WORKER.postMessage({ action: "readFile", payload: [dbFileEl.files[0], getOvr()] })
    });

    dbFileEl.parentElement.addEventListener("dragover", e => e.preventDefault());
    dbFileEl.parentElement.addEventListener("drop", e => {
        e.preventDefault();
        //* msg
        WORKER.postMessage({ action: "readFile", payload: [e.dataTransfer.files[0], getOvr()] })
    });
}

function log(data) {
    if (!gtag) return
    let name = data.name
    delete data.name
    gtag('event', name, data)
}
listenFileChange();

// Who doesn't love stupid ways of solving simple problems?
function showLastUpdate() {
    let t, s
    document.body.childNodes.forEach(node => {
        if (node.nodeType == Node.COMMENT_NODE) {
            let m = node.textContent.match("Deploy Timestamp: (.+) ")
            if (m) {
                t = new Date(m[1])
            }
            else {
                m = node.textContent.match("SHA: ([0-9a-z]+)")
                if (m) {
                    s = m[1]
                }
            }
        }
    })
    if (t && s) {
        document.querySelector("#upd-time").textContent = t.toDateString()
        let link = document.querySelector("#upd-sha")
        link.href = `${document.querySelector("#repo-link").href}/commit/${s}`
        link.textContent = s
    }
    else document.querySelector("#upd-info").style.visibility = "hidden"
}
showLastUpdate()