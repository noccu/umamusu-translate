importScripts("https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.4.0/dist/sql-wasm.js");
const sql_wasm_path = "https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.4.0/dist";

// Put SQL and Database as global variable
let SQL;

onmessage = function ({ data: { action, payload } }) {
    if (self[action] && typeof self[action] == "function") {
        self[action].apply(this, Array.isArray(payload) ? payload : [payload]);
    }
}

// append timestamp to get fresh copy since github pages caching is aggressive
async function fetchJSON(file) {
    const timestamp = new Date().getTime();
    const body = await fetch(`${file}?${timestamp}`);
    return body.json();
}

// savedb exports the db as a downloadable file to the user
function saveDB(db) {
    const createBlob = (data, mimeType) => {
        const blob = new Blob([data], {
            type: mimeType
        })
        return self.URL.createObjectURL(blob)
    }

    const data = db.export();
    let blobUrl = createBlob(data, "application/x-sqlite3");
    postMessage({ action: "saveDB", payload: blobUrl })
};

// process translates the loaded db and exports it
function process(db, data, { table, field }) {
    const findAndReplaceStatement = db.prepare(`UPDATE ${table} SET ${field}=:replace WHERE ${field}=:search`);

    // Search and replace for every item in data.json
    for (const jpText in data) {
        const enText = data[jpText];
        //* msg
        postMessage({ action: "process" })
        if (!enText) continue; // Skip if enText is empty

        // console.log(`Replacing ${jpText} with ${enText}!`);
        findAndReplaceStatement.run({
            ":search": jpText,
            ":replace": enText,
        });
    }
    findAndReplaceStatement.free();
};

async function translate(db, opts) {
    const cfg = await fetchJSON("cfg.json");
    let i = 1;

    for (let entry of cfg) {
        let data = await fetchJSON(entry.file);

        //Override
        if (entry.overrides) {
            await optionOverride(data, entry.overrides, opts);
        }
        //* msg
        let payload = {};
        payload.parts = cfg.length == 1 ? "" : ` ${i++}/${cfg.length}`;
        payload.dataMax = Object.keys(data).length;
        postMessage({ action: "translate", payload });

        process(db, data, entry);
    }

    // Serve back to user
    saveDB(db);
};

// loads picked file as sqlite database
// and fires the translation process with the loaded db
function readFile(file, opts) {
    if (!file) return;
    postMessage({action: "log", payload: {name: "create_db", create_type: "start", db_type: opts['opt-skill']}});
    const reader = new FileReader();

    reader.addEventListener("load", async () => {
        let uints = new Uint8Array(reader.result);
        let db = new SQL.Database(uints);
        translate(db, opts);
    });

    initSqlJs({ locateFile: file => `${sql_wasm_path}/${file}` })
        .then(sqlJs => {
            SQL = sqlJs;
            reader.readAsArrayBuffer(file);
        });
}

function optionOverride(data, list, chosen) {
    for (let [name, ovr] of Object.entries(list)) {
        let file = ovr[chosen[name]];
        if (file) {
            return fetchJSON(file).then(newJson => {
                for (let [key, val] of Object.entries(newJson)) {
                    data[key] = val;
                }
            })
        }
    }
}