import fs from "fs"

//* This script translates random but unchanging shit that's too annoying to do manually.

//* For support-full-name.json and support-effect-unique-name.json — support-title.json and uma-name.json need to be translated first.
//* For factor-desc.json — skill-name.json needs to be translated first and common.json needs to be kept up to date.

const FILES = {
        trainerReq: "translations/mdb/trainer-title-requirements.json",
        missions: "translations/mdb/missions.json",
        storyMissions: "translations/mdb/story-event-missions.json",
        umaNames: "translations/mdb/uma-name.json",
        trTitles: "translations/mdb/trainer-title.json",
        races: "translations/mdb/race-name.json",
        pieces: "translations/mdb/item-uma-pieces.json",
        skills: "translations/mdb/skill-name.json",
        spTitles: "translations/mdb/support-title.json",
        spFullNames: "translations/mdb/support-full-name.json",
        spUniqueNames: "translations/mdb/support-effect-unique-name.json",
        misc: "translations/mdb/miscellaneous.json",
        factors: "translations/mdb/factor-desc.json",
        common: "translations/mdb/common.json",
        shoeSize: "translations/mdb/uma-profile-shoesize.json",
        lessonEffects: "translations/mdb/lesson-effects.json",
        items: "translations/mdb/item-desc.json"
    }
const UNCOMMON_FILES = [
    "shoeSize",
    "lessonEffects",
    "items"
]
const PFILES = {};
const FAN_AMOUNT = {
    "1000万": "10 million",
    "5000万": "50 million",
    "1億": "100 million"
}
const TRAINER_TITLE = {
    "との出会い": "Memories with $",
    "担当": "$'s Personal Trainer",
    "専属": "$'s Exclusive Trainer",
    "名手": "Masterful $ Trainer",
    "全冠": "Fully-crowned $"
}
const CM_GRADE = {
    "プラチナ": "Platinum",
    "ゴールド": "Gold",
    "シルバー": "Silver",
    "ブロンズ": "Bronze"
}
const CM_RESULT = {
    "伝説的な": "legendary",
    "偉大な": "glorious",
    "輝かしい": "notable",
    "優れた": "remarkable"
}

function readFiles() {
    for (let file of Object.keys(FILES)) {
        if (!UPDATE_UNCOMMON && UNCOMMON_FILES.includes(file)) continue
        PFILES[file] = JSON.parse(fs.readFileSync(FILES[file], "utf8"))
    }
    console.log("Files read.");
}

function translate() {
    //missions first so trainer reqs can copy from it
    for (let [jpText, enText] of Object.entries(PFILES.missions.text)) {
        if (enText) continue; //skip translated entries
        translateSpecific("g1-3", jpText, PFILES.missions)
        translateSpecific("e4s", jpText, PFILES.missions)
        translateSpecific("fan", jpText, PFILES.missions)
        translateSpecific("gend", jpText, PFILES.missions)
        translateSpecific("stad", jpText, PFILES.missions)
        translateSpecific("wake", jpText, PFILES.missions)
        translateSpecific("star", jpText, PFILES.missions)
        translateSpecific("lbsupp", jpText, PFILES.missions)
        translateSpecific("friend", jpText, PFILES.missions)
        translateSpecific("genLimMiss", jpText, PFILES.missions)
        translateSpecific("skillMis", jpText, PFILES.missions)
        translateSpecific("affec", jpText, PFILES.missions)
    }
    // story-event-missions.json
    for (let [jpText, enText] of Object.entries(PFILES.storyMissions.text)) {
        if (enText) continue; //skip translated entries
        translateSpecific("g1-3", jpText, PFILES.storyMissions)
        translateSpecific("genLimMiss", jpText, PFILES.storyMissions)
    }
    for (let [jpText, enText] of Object.entries(PFILES.trainerReq.text)) {
        if (enText) {
            if (enText.includes(" Hai")) {
                translateSpecific("cmRes", jpText, PFILES.trainerReq)
            }
            continue
        }; //skip header and translated entries
        if (PFILES.missions.text[jpText]) PFILES.trainerReq.text[jpText] = PFILES.missions.text[jpText] //copy dupes
        translateSpecific("g1-3", jpText, PFILES.trainerReq)
        translateSpecific("e4s", jpText, PFILES.trainerReq)
        translateSpecific("fan", jpText, PFILES.trainerReq)
    }
    for (let [jpText, enText] of Object.entries(PFILES.trTitles.text)) {
        if (enText) {
            if (enText.includes(" Hai")) {
                translateSpecific("cmGrade", jpText, PFILES.trTitles)
            }
            continue
        }; //skip header and translated entries
        translateSpecific("trTitle", jpText, PFILES.trTitles)
    }
    for (let [jpText, enText] of Object.entries(PFILES.pieces.text)) {
        if (enText) {
            continue
        }; //skip header and translated entries
        translateSpecific("piece", jpText, PFILES.pieces)
    }
    
    //* support-full-name.json
    for (let [jpText, enText] of Object.entries(PFILES.spFullNames.text)) {
        if (enText) continue;
        let [,fullTitle, titleName, umaName] = jpText.match(/(\[(.*)\])(.*)/)
        if (PFILES.spTitles.text[fullTitle]) {
            fullTitle = PFILES.spTitles.text[fullTitle]; //replace var with EN ver
            if (Object.hasOwn(PFILES.spUniqueNames.text, titleName) && !PFILES.spUniqueNames.text[titleName]) {
                PFILES.spUniqueNames.text[titleName] = fullTitle.replace(/\[|\]/g, ""); //write en pure title, using previous var
            }
        }

        if (PFILES.umaNames.text[umaName]) {
            umaName = PFILES.umaNames.text[umaName]; //replace var with en ver
        }
        else if (PFILES.misc.text[umaName]) {
            umaName = PFILES.misc.text[umaName]; //replace var with en ver
        }
        PFILES.spFullNames.text[jpText] = `${fullTitle} ${umaName}`; //write full name, whichever parts were found
    }

    //*factor-desc.json
    for (let [jpText, enText] of Object.entries(PFILES.factors.text)) {
        if (enText) continue;
        let skillName = undefined, commonName = undefined, hasApt = undefined
        let m = jpText.match(/「(.+)」のスキル/)
        if (m) {
            [,skillName] = m
            if (PFILES.skills.text[skillName]) {
                skillName = PFILES.skills.text[skillName]; //replace var with EN ver
            }
        }
        m = jpText.match(/(.+?)(適性)?がアップ/)
        if (m) {
            [,commonName, hasApt] = m
            commonName = commonName.split("と")
            commonName.forEach((name, idx) => {
                if (PFILES.common.text[name]) {
                    commonName[idx] = PFILES.common.text[name]; //replace var with en ver
                }
            })
            commonName = commonName.join(" and ")
        }
        let fullString = ""
        if (commonName) fullString += `Increases ${commonName}${hasApt ? " aptitude" : ""}`
        if (skillName) fullString += `${commonName? ", g" : "G"}ain skill hint: ${skillName}`
        if (fullString) {
            PFILES.factors.text[jpText] = `<size=22>${fullString}\\n</size>`; //write full name, whichever parts were found
        }
    }

    for (let [jpText, enText] of Object.entries(PFILES.races.text)) {
        if (enText) continue; //skip translated entries
        translateSpecific("legvs", jpText, PFILES.races)
    }

    //! uncommons down here
    if (!UPDATE_UNCOMMON) return

    //*shoe-size.json
    for (let [jpText, enText] of Object.entries(PFILES.shoeSize.text)) {
        if (enText) continue;
        let out = ""
        let m = jpText.matchAll(/([左右]|左右ともに)：?([\d.]+(?:cm|㎝))(?:\\n|([（\(].+)$)?/mg)
        for (let p of m) {
            let [,side, val, rest] = p
            if (side == "左") {
                out += "Left: " + val
            }
            else if (side == "右"){
                out += " \\nRight: " + val
            }
            else {
                out += "Both: " + val
            }
            if (rest) out += rest
            PFILES.shoeSize.text[jpText] = out
        }
    }

    //* lesson-effects
    for (let [jpText, enText] of Object.entries(PFILES.lessonEffects.text)) {
        if (enText) continue;
        enText = []
        let matches
        if (jpText.startsWith("＜")) {
            matches = jpText.matchAll(/＜(?:作戦・)?(.+?)＞のスキルヒントLv (<color=#[a-z0-9]+>\+[\d～]+<\/color>)(?:\\n)?/img)
            for (let m of matches) {
                let [,apt, effect] = m
                if (PFILES.common.text[apt]) {
                    enText.push(`${PFILES.common.text[apt]} Skill Hint Lv ${effect}`)
                }
            }
        }
        else {
            matches = jpText.matchAll(/(.+?) (<color=#[a-z0-9]+>\+[\d～]+<\/color>)(?:\\n)?/img)
            for (let m of matches) {
                let [,stat, effect] = m
                if (PFILES.common.text[stat]) {
                    enText.push(`${PFILES.common.text[stat]} ${effect}`)
                }
            }
        }
        PFILES.lessonEffects.text[jpText] = enText.join("\\n"); //write full name, whichever parts were found
    }

    //* item-desc
    for (let [jpText, enText] of Object.entries(PFILES.items.text)) {
        if (enText) continue;

        let [,umaName] = jpText.match(/(.+)の手作りチョコ/)
        let umaNameEn = PFILES.umaNames[umaName]
        if (umaNameEn) {
            PFILES.items.text[jpText] = `<size=22>Handmade by ${umaNameEn}. Restores 30TP upon use.\\n</size>`;
        }
    }
}

/**
 * @param {string} jpText 
 * @param {{string: string}} data
 */
function translateSpecific (type, jpText, file) {
    let m;
    let data = file.text;
    if (type == "g1-3") {
        m = jpText.match(/(.+)でGⅠ～GⅢの\\n全てのトロフィーを獲得しよう/)
        if (m) {
            let [,umaName] = m, umaNameEn = PFILES.umaNames.text[umaName];
            if (umaNameEn) {
                data[jpText] = `Obtain all G1-G3 trophies with ${umaNameEn}`;
            }
        }
    }
    else if (type == "e4s") {
        m = jpText.match(/(.+)の\\nウマ娘ストーリー第4話を見よう/)
        if (m) {
            let [,umaName] = m, umaNameEn = PFILES.umaNames.text[umaName];
            if (umaNameEn) {
                data[jpText] = `Read chapter 4 of ${umaNameEn}'s story`;
            }
        }
    }
    else if (type == "fan") {
        m = jpText.match(/(.+)のファン数を\\n累計(\d+[万億])人獲得しよう/)
        if (m) {
            let [,umaName, amount] = m, umaNameEn = PFILES.umaNames.text[umaName];
            if (umaNameEn) {
                data[jpText] = `Reach ${FAN_AMOUNT[amount]} total fans for ${umaNameEn}`;
            }
        }
    }
    else if (type == "gend") {
        m = jpText.match(/育成ウマ娘(\d+)人の\\nグッドエンディングをみよう/)
        if (m) {
            let [, amount] = m
            data[jpText] = `Reach ${amount} horsegirls' Good End`;
        }
    }
    else if (type == "stad") {
        m = jpText.match(/チーム競技場を\\n(\d+)回プレイしよう/)
        if (m) {
            let [, amount] = m
            data[jpText] = `Play in the Team Stadium ${amount} times`;
        }
    }
    else if (type == "wake") {
        m = jpText.match(/育成ウマ娘の覚醒Lvを\\n(\d+)回上げよう/)
        if (m) {
            let [, amount] = m
            data[jpText] = `Awaken a horsegirl ${amount} times`;
        }
    }
    else if (type == "star") {
        m = jpText.match(/育成ウマ娘を才能開花で\\n(\d+)回★を上げよう/)
        if (m) {
            let [, amount] = m
            data[jpText] = `Gain ${amount}★ through talent blooming horsegirls`;
        }
    }
    else if (type == "lbsupp") {
        m = jpText.match(/サポートカードを\\n(\d+)回上限解放しよう/)
        if (m) {
            let [, amount] = m
            data[jpText] = `Limit break a support card ${amount} times`;
        }
    }
    else if (type == "friend") {
        m = jpText.match(/(.+)の\\n親愛度ランクを1にしよう/)
        if (m) {
            let [,umaName] = m, umaNameEn = PFILES.umaNames.text[umaName];
            if (umaNameEn) {
                data[jpText] = `Reach friendship rank 1 with ${umaNameEn}`;
            }
        }
    }
    else if (type == "trTitle") {
        m = jpText.match(/(.+)(との出会い|担当|専属|名手|全冠)/)
        if (m) {
            let [,umaName, title] = m, umaNameEn = PFILES.umaNames.text[umaName];
            if (umaNameEn && title) {
                data[jpText] = TRAINER_TITLE[title].replace("$", umaNameEn).replace("s's", "s'");
            }
        }
    }
    else if (type == "cmGrade") {
        let enText = data[jpText]
        if (!enText.endsWith(" Hai")) return
        m = jpText.match(/杯(プラチナ|ゴールド|シルバー|ブロンズ)/)
        if (m) {
            let [, grade] = m;
            if (grade && enText) {
                data[jpText] = `${enText} ${CM_GRADE[grade]}${jpText.endsWith("★") ? " ★" : ""}`;
            }
        }
    }
    else if (type == "cmRes") {
        let enText = data[jpText]
        if (enText.length > 22) return
        m = jpText.match(/杯で(?:(\d)回)?(.+)成績/)
        if (m) {
            let [, i, res] = m;
            i = i ? `${i}x ` : ""
            if (res && enText) {
                data[jpText] = `Achieve ${i}${CM_RESULT[res]} results in the ${enText}`;
            }
        }
    }
    else if (type == "genLimMiss") {
        let out = "", race, txtKey = jpText, found = true;
        m = jpText.match(/【(.+)】(.+)/)
        if (m) {
            [, race, jpText] = m
            if (race == "デイリー") out = `[Daily] `
            else if (race == "期間限定") out = `[Time-Limited] `
            else if (PFILES.races.text[race]) out = `[${PFILES.races.text[race]}] `
            else out = `[${race}]`
        }

        if (m = jpText.match(/育成を(\d+)回完了しよう/)) {
            let [, n] = m;
            out += `Complete training ${n} time${n > 1 ? "s" : ""}`;
        }
        else if (m = jpText.match(/(育成で)?(.+)に.*勝利しよう/)) {
            let [, t, r] = m;
            r = PFILES.races.text[r]
            if (r) {
                out += `Win ${r}${t ? " in training" : ""}`;
            }
        }
        else if (m = jpText.match(/育成で(.+?)の?(\d)着以内に入ろう/)) {
            let [, r, p] = m;
            r = PFILES.races.text[r]
            if (r) {
                out += `Finish top ${p} in ${r} during training`;
            }
        }
        else if (m = jpText.match(/(.+)（(.+)）に出走しよう/)) {
            let [, umaJp, diff] = m;
            let umaEn = PFILES.umaNames.text[umaJp]
            if (umaEn) {
                out += `Challenge ${umaEn} (${diff})`;
            }
        }
        else if (m = jpText.match(/(.+)に(\d+)回出走しよう/)) {
            let [, race, n] = m;
            let raceEn = PFILES.races.text[race]
            if (raceEn) {
                out += `Enter ${raceEn} ${n} times`;
            }
        }
        else if (m = jpText.match(/カーニバルPtを累計\\n(\d+)Pt獲得しよう/)) {
            let [, pt] = m;
            if (pt) {
                out += `Obtain ${pt} total Carnival Pts`;
            }
        }
        else if (jpText.match(/限定ミッションを(?:すべて|全て)クリアしよう/)) {
            out += "Complete all limited missions";
        }
        else if (m = jpText.match(/全ての育成目標を達成して(\d+)回育成完了しよう/)) {
            let [, n] = m;
            if (n) {
                out += `Clear all training goals ${n} times`;
            }
        }
        else {
            found = false
        }

        if (found){
            data[txtKey] = out
        }
    }
    else if (type == "piece") {
        m = jpText.match(/(.+)のピース/)
        if (m) {
            let [,umaName] = m, umaNameEn = PFILES.umaNames.text[umaName];
            if (umaNameEn) {
                data[jpText] = `${umaNameEn}'s piece`;
            }
        }
    }
    else if (type == "skillMis") {
        m = jpText.match(/(.+)を獲得し育成完了/)
        if (m) {
            let [,skills] = m
            skills = skills.replace("\\n", "").split("/")
            let i = 0
            for (let skill of skills) {
                let skillEn = PFILES.skills.text[skill];
                if (skillEn) {
                    skills[i] = skillEn
                }
                i++
            }
            data[jpText] = `Complete training having acquired ${skills.join(", ")}`;
        }
    }
    else if (type == "legvs") {
        m = jpText.match(/レジェンドレース　VS(.+)/)
        if (m) {
            let [,umaName] = m, umaNameEn = PFILES.umaNames.text[umaName];
            if (umaNameEn) {
                data[jpText] = `VS ${umaNameEn}`;
            }
        }
    }
    else if (type == "affec") {
        m = jpText.match(/(.+?)の\\n親愛度ランクを(\d+)にしよう/)
        if (m) {
            let [,umaName, rank] = m, 
                umaNameEn = PFILES.umaNames.text[umaName];
            if (umaNameEn) {
                data[jpText] = `Raise ${umaNameEn}'s \\naffection to rank ${rank}`;
            }
        }
    }
}

function writeFiles() {
    // Don't change files only used for lookup
    delete PFILES.umaNames;
    // delete PFILES.races;
    delete PFILES.skills;
    delete PFILES.spTitles;
    delete PFILES.misc;
    delete PFILES.common;
    for (let [file, content] of Object.entries(PFILES)) {
        if (!UPDATE_UNCOMMON && UNCOMMON_FILES.includes(file)) continue
        fs.writeFileSync(FILES[file], JSON.stringify(content, null, 4), "utf-8");
    }
}

const UPDATE_UNCOMMON = process.argv.includes("-unc")
console.log("Reading...");
readFiles();
console.log("Translating...");
translate();
console.log("Writing...");
writeFiles();
