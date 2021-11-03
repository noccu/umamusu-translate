// ==UserScript==
// @name        deepl-translator
// @namespace   https://github.com/noccu/
// @match       https://www.deepl.com/en/translator
// @grant       GM_registerMenuCommand
// @version     1.3
// @author      noccu
// @description Translate API for DeepL using WebSockets
// ==/UserScript==

//todo: remove userscript data and use with selenium

'use strict'

class Translator {
    input = document.querySelector("textarea.lmt__source_textarea")
    output = document.querySelector("textarea.lmt__target_textarea")
    tl = false
    obs = new MutationObserver(this.rcvText.bind(this))
    r = undefined
    clearText = false // DeepL seems to be affected by previous text sometimes. This might good for sequential text like stories (?), perhaps not for random text.
    timeout = 5000
    retries = 3

    constructor(clear) {
        this.obs.observe(document.querySelector("#target-dummydiv"), { childList: true })
        if (clear) this.clearText = clear
        // this.output.addEventListener("input", this.rcvText.bind(this))
    }
    sendText(txt) {
        this.tl = true
        this.input.value = txt
        this.input.dispatchEvent(new InputEvent("input"))
        let attempt = 0
        this.interval = setInterval(() => {
            if (attempt < this.retries) {
                console.log(`No response from DeepL after ${this.timeout/1000}s. Retrying entry... (${attempt+1}/${this.retries})`)
                this.input.dispatchEvent(new InputEvent("input"))
                attempt++;
            }
            else {
                console.log("Adding space to attempt unlock...")
                this.input.value += " "
                this.input.dispatchEvent(new InputEvent("input"))
                clearInterval(this.interval)
            }
        }, this.timeout)
        return new Promise(r => this.r = r)
    }
    rcvText() {
        if (!this.tl || !this.output.value) return
        this.tl = false
        clearInterval(this.interval)
        if (this.r) {
            if (this.clearText) this.input.value = ""
            this.r(this.output.value)
            this.r = undefined
        }
        else console.error("Received translation but no Promise set.") // This should never trigger
    }
}

let PREV_TL
const DEEPL = new Translator(true)

async function getTranslatedText(srcText) {
    let tl = await DEEPL.sendText(srcText)
    // if (tl == PREV_TL) { throw "Translated text has not changed" }
    PREV_TL = tl
    return tl;
}

function msgHandler(msg) {
    msg = JSON.parse(msg.data)
    console.log("Received message", msg)
    if (msg.action == "tl") {
        getTranslatedText(msg.text).then(
            dstTxt => this.send(JSON.stringify({ action: "tl-res", text: dstTxt }))
        )
    }
}

function main() {
    const ws = new WebSocket("ws:localhost:61017")
    ws.onmessage = msgHandler.bind(ws)
    ws.onopen = e => {
        console.log(e)
        ws.send(`{"action": "connect"}`)
    }
}


GM_registerMenuCommand("Connect WebSocket", main);
