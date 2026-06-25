// ==UserScript==
// @name        Keypress Sounds
// @namespace   myxi-tc-keypress-sounds
// @icon        https://typecelerate.com/favicon.ico
// @version     1.0.0
//
// @match       https://typecelerate.com/*
// @resource    PACK https://files.catbox.moe/xp0emj.kps
// @grant       GM_getResourceURL
// @grant       GM_xmlhttpRequest
// @inject-into content
//
// @author      eeriemyxi (github)
// @description A project that lets you use play custom sounds when you press keys on any website you let it to.
// ==/UserScript==

function parseKps(buf) {
    let cursor = 0;
    const view = new DataView(buf)
    const nframes = []

    const fileCount = view.getUint32(cursor, true)
    cursor += 4;

    for (let i = 1; i <= fileCount; i++) {
        const start = view.getUint32(cursor, true);
        cursor += 4;
        const end = view.getUint32(cursor, true);
        cursor += 4;
        nframes.push({start, end})
    }

    return {
        fileCount,
        nframes,
        data: buf.slice(cursor)
    }
}

const PACK_URL = GM_getResourceURL("PACK");

let audioCtx = null;
let packAudioBuf = null;
let tcsel = null;

GM_xmlhttpRequest({
    method: "GET",
    url: PACK_URL,
    responseType: "arraybuffer",
    onload: async (resp) => {
        tcsel = parseKps(resp.response)
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        packAudioBuf = await audioCtx.decodeAudioData(tcsel.data)
    }
})

document.addEventListener("keydown", async (event) => {
    if (!tcsel || !packAudioBuf) return;

    if (audioCtx.state === "suspended") {
        await audioCtx.resume()
    }

    const frame = tcsel.nframes[Math.floor(Math.random() * tcsel.nframes.length)]
    const src = audioCtx.createBufferSource()

    const start = frame.start / packAudioBuf.sampleRate
    const end = frame.end / packAudioBuf.sampleRate
    const duration = end - start

    src.buffer = packAudioBuf;
    src.connect(audioCtx.destination)
    src.start(0, start, duration)
})
