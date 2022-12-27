import fs from "fs"
import https from "https"
import {parse as htmlParse} from 'node-html-parser';

let nameSource = "translations/mdb/uma-name.json"
let baseUrl = "https://gametora.com/umamusume/characters/"

function readFile(path) {
    return JSON.parse(fs.readFileSync(path, "utf8"))
}
function writeFile(path, data) {
    fs.writeFileSync(path, JSON.stringify(data, null, 4), "utf-8");
}

function lookupHorse(name) {
    return new Promise((r, x) => {
        let gtUrl = baseUrl + name.replaceAll(" ", "-").toLowerCase()
        console.log(gtUrl)
        https.get(gtUrl, onGotData);
        function onGotData(res) {
            if (res.statusCode != 200) {
                console.log("Bad response")
                r(undefined)
                return
            }
            var chunks = [];
            res.on('data', loadChunk);
            res.on('end', onEnd);
            function loadChunk(chunk) {
                chunks.push(chunk);
            }
            function onEnd() {
                chunks = chunks.join('');
                r(chunks)
            }
        }
    })
}

function parseData(htmlData) {
    let dom = htmlParse(htmlData)
    let jsonData = dom.querySelector("#__NEXT_DATA__")
    if (!jsonData) {
        console.log("no json")
        return
    }
    return JSON.parse(jsonData.textContent)
}

function cleanText(t) {
    return t.replace(/\n|\\n/g, "")
}

function mdbMap(o) {
    o.map = {}
    for (let k of Object.keys(o.data.text)) {
        o.map[cleanText(k)] = k
    }
}

const dataFiles = {
    "family": {path: "translations/mdb/uma-profile-family.json"},
    "ears": {path: "translations/mdb/uma-profile-ears.json"},
    "tail": {path: "translations/mdb/uma-profile-tail.json"},
    "self_intro": {path: "translations/mdb/uma-profile-intro.json"},
    "strong": {path: "translations/mdb/uma-profile-strengths.json"},
    "weak": {path: "translations/mdb/uma-profile-weaknesses.json"},
    "secrets": {path: "translations/mdb/uma-secrets.json"}
}
const vaData = {path: "translations/mdb/seiyuu.json"}
for (let f of Object.keys(dataFiles)) {
    dataFiles[f]["data"] = readFile(dataFiles[f].path)
    mdbMap(dataFiles[f])
}
vaData.data = readFile(vaData.path)

let pinky = []
let nameData = readFile(nameSource)
for (let enName of Object.values(nameData.text)) {
    pinky.push(lookupHorse(enName).then(gtData => {
        if (!gtData) {
            console.log("no gt data")
            return
        }
        gtData = parseData(gtData)

        let prof = gtData.props.pageProps.profileData
        for (let [k, file] of Object.entries(dataFiles)) {
            let text = file.data.text
            if (k == "secrets") {
                let i = 0
                for (let jpText of prof.ja[k]) {
                    jpText = file.map[jpText]
                    if (!jpText) continue
                    if (text.hasOwnProperty(jpText) && text[jpText] == "") {
                        text[jpText] = prof.en[k][i]
                    }
                    i++
                }
            }
            else {
                let jpText = file.map[prof.ja[k]]
                if (!jpText) continue
                if (text.hasOwnProperty(jpText) && text[jpText] == "") {
                    text[jpText] = prof.en[k]
                    console.log(`wrote: ${jpText} = ${prof.en[k]}`)
                }
            }
        }

        let va = gtData.props.pageProps.charData
        let data = vaData.data.text
        let jpText = va.va_ja
        if (data.hasOwnProperty(jpText) && data[jpText] == "") {
            data[jpText] = va.va_en
        }
    }))
}


await Promise.all(pinky)
for (let f of Object.values(dataFiles)) {
    writeFile(f.path, f.data)
}
writeFile(vaData.path, vaData.data)
