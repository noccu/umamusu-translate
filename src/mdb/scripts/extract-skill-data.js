//Node 17.0.1
import sqlite3 from "better-sqlite3";
import fs from "fs";
import { join as pathJoin } from "path";

const DB_PATH = process.argv[2] || pathJoin(process.env.LOCALAPPDATA, "../LocalLow/Cygames/umamusume/master/master.mdb");
const DATA_TL_PATH = "src/mdb/skillData.json"
// H-haha harold.jpg
const SQL_STMT = `select text, skill_data.id,
            float_ability_time_1, precondition_1, condition_1, float_cooldown_time_1,
                ability_type_1_1, float_ability_value_1_1, ability_value_usage_1_1,  target_type_1_1, target_value_1_1,
                ability_type_1_2, float_ability_value_1_2, ability_value_usage_1_2, target_type_1_2, target_value_1_2,
                ability_type_1_3, float_ability_value_1_3, ability_value_usage_1_3, target_type_1_3, target_value_1_3,
            float_ability_time_2, precondition_2, condition_2, float_cooldown_time_2,
                ability_type_2_1, float_ability_value_2_1, ability_value_usage_2_1, target_type_2_1, target_value_2_1,
                ability_type_2_2, float_ability_value_2_2, ability_value_usage_2_2, target_type_2_2, target_value_2_2,
                ability_type_2_3, float_ability_value_2_3, ability_value_usage_2_3, target_type_2_3, target_value_2_3
                    from text_data
                    inner join skill_data on text_data."index" = skill_data.id
                    where text_data.category = 48;`;
const DATA_TL = JSON.parse(fs.readFileSync(DATA_TL_PATH, "utf-8"));

(function main() {
    let outPath = "translations/mdb/alt/skill-desc.json"
    let jsonOut;
    try {
        jsonOut = JSON.parse(fs.readFileSync(outPath, "utf-8"))
    }
    catch (e) {
        if (e.code !== 'ENOENT') throw e
        jsonOut = {'version': 101, 'type': "mdb", 'lineLength': 0};
    }
    jsonOut['text'] = {}
    const db = sqlite3(DB_PATH);
    const stmt = db.prepare(SQL_STMT).raw(true);
    let res = stmt.all();
    db.close();
    res.forEach(row => {
        let [skill, id, ...data] = row;
        jsonOut['text'][skill] = translateData(id, data);
    });
    fs.mkdirSync("translations/mdb/alt", {recursive: true})
    fs.writeFileSync(outPath, JSON.stringify(jsonOut, null, 4));
})();

function translateData(id, sqlData) {
    //harold.png
    let [duration, precondition, conditions, cooldown,
        type, strength, strengthMod, targetType, targetValue,
        type2, strength2, strengthMod2, targetType2, targetValue2,
        type3, strength3, strengthMod3, targetType3, targetValue3,
        ...skill2] = sqlData;

    let outString = "<b>" + translateEffect(id, type, strength, strengthMod);
    if (targetType > 1) outString += translateTarget(targetType, targetValue);

    if (type2) outString += `, ${translateEffect(id, type2, strength2, strengthMod2)}`;
    if (targetType2 > 1) outString += translateTarget(targetType2, targetValue2);

    if (type3) outString += `, ${translateEffect(id, type3, strength3, strengthMod3)}`;
    if (targetType3 > 1) outString += translateTarget(targetType3, targetValue3);

    if (duration == -1) { duration = "indefinitely"; }
    else if (duration == 0) { duration = "immediately"; }
    else { duration = "for " + parseInt(duration) / 10000 + "s"; }
    outString += ` ${duration}</b>`;

    cooldown /= 10000 // in seconds, then limit to potentially usable range
    if (cooldown > 0 && cooldown < 90) {
        outString += ` (CD ${cooldown}s)`
    }

    outString += ` when: ${translateConditions(conditions)}`;
    if (precondition) outString += ` <color=#29b39e>after</color>: ${translateConditions(precondition)}`

    if (skill2.length && skill2[2] != 0) { outString += "\\n" + translateData(id, skill2) }
    return outString;
}
function translateEffect(id, type, strength, strengthMod) {
    if (DATA_TL.specialId[id]) return DATA_TL.specialId[id];
    else if (strength == 0) return "";
    let effect = DATA_TL.ability_type[type] || "Special",
        format = "";
    strength = strength / 10000;
    if (strengthMod > 1) {
        strengthMod = DATA_TL.ability_value_usage[strengthMod]
    }
    else {
        strengthMod = false
    }

    //todo: find something better, if needed...
    if (Array.isArray(effect)) {
        format = effect[1]
        if (effect[2]) {
            strength = transformValue(strength, effect[2]);
        }
        effect = effect[0];        
    }

    if (format == "%") { strength = strength.toLocaleString(undefined, {style: "percent", signDisplay:"exceptZero", useGrouping: false, maximumFractionDigits: 1}) }
    else { strength = strength.toLocaleString(undefined, {style: "decimal", signDisplay:"exceptZero", useGrouping: false, maximumFractionDigits: 2}) + format }
    
    return `${effect} ${strength}${strengthMod ? " " + strengthMod : ""}`;
}

function transformValue(val, transforms) {
    let t = transforms.split(" ")
    for (let i = 0; i < t.length; i++) {
        let action = t[i]
        let m = action.match(/(\d+)-/)
        if (m) val = m[1] - val
        else if (action == "inv") val *= -1
        else if (action == "%") val /= 100
        else if (action == "rep") {
            val = t[++i]
            i++
        }
    }
    return val
}

function translateTarget(type, value) {
    if (type == 0 || type == 1) return "";
    type = DATA_TL.target_type[type];
    let val = DATA_TL.target_value[value];
    return ` to ${val || `${value} closest`} ${type}`;
}
function translateConditions(conditions) {
    if (!conditions) return "Always"
    let orSplit = conditions.split("@");
    orSplit.forEach((expr, idx) => {
        let andSplit = expr.split("&");
        andSplit.forEach((cond, idx) => {
            let [, name, op, val] = cond.match(/([a-z_0-9]+)([=!<>]+)(\d+)/);
            let condData = DATA_TL.conditions[name];
            if (!condData) {
                andSplit[idx] = `${name} ${op} ${val}`; //better text flow in game at the cost of some readability
                return;
            }
            let text = condData.string || condData[op];
            if (!text) return; //just in case
            if (Array.isArray(text)) {
                val = transformValue(val, text[1]);
                text = text[0];
            }
            andSplit[idx] = text.replace("$", () => {
                return condData.lookup?.[val] || condData.lookup?.default || val;
            });
        });
        orSplit[idx] = andSplit.join(" AND ");
    });

    conditions = orSplit.join(" OR ");
    return conditions;
}