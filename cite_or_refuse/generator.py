"""Seeded generator for the synthetic case.

Everything here is fictional: the town (Harlow Creek), the people, the case number and every line of
"evidence". The same seed always produces byte-identical output.

Run:  python -m cite_or_refuse.generator [--out data]
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

SEED = 2009
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

CASE = {
    "case_id": "HCPD 09-0314-H",
    "title": "Quick Stop Market robbery-homicide (fictional)",
    "town": "Harlow Creek",
    "incident_date": "2009-03-14",
    "summary": (
        "Clerk Marcus Bell was shot during a robbery of the Quick Stop Market on Route 9 in the invented town "
        "of Harlow Creek. The case went cold and was reopened in 2018, when jail calls from Merritt County "
        "Jail were reviewed."
    ),
}

# Canonical name -> aliases used in text. Used by the answerer to resolve "Dre", "Kev", etc.
PEOPLE = {
    "Andre Whitfield": ["andre", "whitfield", "dre", "andre w."],
    "Tasha Greene": ["tasha", "greene"],
    "Enrique Banks": ["rico", "enrique", "banks"],
    "Loretta Whitfield": ["loretta"],
    "Jamal Pierce": ["jamal", "pierce"],
    "Kevin Lopez": ["kevin", "kev", "lopez", "k. lopez"],
    "Maria Lopez": ["maria"],
    "Luis Ortega": ["luis", "ortega", "big lou"],
    "Marcus Bell": ["marcus", "bell"],
    "Darnell Bell": ["darnell"],
    "Gloria Fenn": ["gloria", "fenn"],
    "Paul Ortiz": ["paul", "ortiz"],
    "Hector Ruiz": ["hector", "ruiz"],
    "Det. Renee Okafor": ["okafor", "renee"],
    "Ofc. Dana Marsh": ["marsh", "dana"],
}

SYSTEM = "SYSTEM"
SYSTEM_LINE = "This call is from an inmate at Merritt County Jail and is subject to monitoring and recording."

INMATE_FILLER = [
    "They got us on lockdown again, nobody moving till Thursday.",
    "Put something on my books when you can, like forty.",
    "The food in here is terrible, it's the same thing every day.",
    "My lawyer said the court date got pushed to next month.",
    "Tell the kids I said hi, tell them I love them.",
    "It's loud in here, I can barely hear you.",
    "These phones cut off after fifteen minutes, so listen.",
    "You seen the game Sunday? They got blown out.",
    "I been reading a lot, trying to keep my head right.",
    "They moved my cellie out, new dude snores like crazy.",
    "On everything, I'm good, don't worry about me.",
    "Nah, for real.",
    "Facts, facts.",
    "Hold on, hold on, somebody yelling.",
    "[inaudible] said they gonna move me to C block.",
    "I signed up for the GED class, starts in two weeks.",
    "Commissary out of noodles again, can you believe that.",
    "Word.",
    "My knee been hurting since I fell on the stairs.",
    "Did the letter come yet? I sent it Monday.",
]

OTHER_FILLER = [
    "I put twenty on there yesterday, check it.",
    "The baby been asking about you.",
    "I'm at work, I only got a minute.",
    "Your auntie said she gonna write you.",
    "You eating okay in there?",
    "Mm-hm.",
    "Yeah.",
    "Okay.",
    "I hear you.",
    "Boy, stop.",
    "Don't start with me today.",
    "It's raining like crazy out here.",
    "I'm gonna try to come up there Saturday for visit.",
    "[crosstalk]",
    "Rent went up again, I'm not playing.",
    "I can't hear you, say that again.",
    "You sound tired.",
    "Everybody at church said they praying for you.",
    "[inaudible] the bus was late again.",
    "I got the paperwork, I'm gonna mail it.",
]

# Calls 1-28: Andre Whitfield. Calls 29-40: Kevin Lopez. (inmate, other, third party or None)
CALL_PARTIES: dict[int, tuple[str, str, str | None]] = {}
_andre_cycle = ["Tasha Greene", "Enrique Banks", "Loretta Whitfield", "Tasha Greene", "Jamal Pierce"]
for _i in range(1, 29):
    CALL_PARTIES[_i] = ("Andre Whitfield", _andre_cycle[(_i - 1) % len(_andre_cycle)], None)
for _i in range(29, 41):
    CALL_PARTIES[_i] = ("Kevin Lopez", "Maria Lopez" if _i % 3 else "Luis Ortega", None)
CALL_PARTIES.update({
    5: ("Andre Whitfield", "Tasha Greene", None),
    8: ("Andre Whitfield", "Tasha Greene", None),
    10: ("Andre Whitfield", "Tasha Greene", None),
    12: ("Andre Whitfield", "Jamal Pierce", None),
    14: ("Andre Whitfield", "Tasha Greene", "Enrique Banks"),
    17: ("Andre Whitfield", "Tasha Greene", None),
    18: ("Andre Whitfield", "Tasha Greene", None),
    20: ("Andre Whitfield", "Loretta Whitfield", None),
    24: ("Andre Whitfield", "Tasha Greene", "Enrique Banks"),
    31: ("Kevin Lopez", "Maria Lopez", None),
    33: ("Kevin Lopez", "Maria Lopez", None),
    36: ("Kevin Lopez", "Maria Lopez", "Luis Ortega"),
})

# Planted exchanges: who is "inmate", "other" or "third".
PLANTS: dict[int, list[tuple[str, str]]] = {
    5: [
        ("other", "They keep asking me where you was back then."),
        ("inmate", "I wasn't even there that night, I was at my mom's watching the game."),
        ("other", "Okay, I'm just telling you what they asking."),
    ],
    8: [
        ("other", "Something I gotta ask you about, and don't get mad."),
        ("inmate", "What now?"),
        ("other", "That watch you had, the gold one, Kev said he took it to Lucky's."),
        ("inmate", "Don't talk about that on this phone."),
    ],
    10: [
        ("inmate", "Listen to me, Tasha."),
        ("inmate", "If them detectives come by, you don't say nothing, you tell them call my lawyer."),
        ("other", "I know, Dre, I know."),
    ],
    12: [
        ("other", "They said they still got that hat from the store."),
        ("inmate", "That hat they got, the red one, that ain't even mine, Rico always wore red."),
        ("other", "Bro, chill."),
    ],
    14: [
        ("third", "Who else on the line?"),
        ("other", "It's just me and you and Dre, Rico."),
        ("third", "Aight, I'm not saying nothing on here anyway."),
    ],
    17: [
        ("inmate", "Tell Rico get rid of the green one, take it out past the quarry in Dunmore."),
        ("other", "Why you keep bringing that up?"),
        ("inmate", "Just tell him, it's been sitting at his cousin's too long."),
    ],
    18: [
        ("inmate", "It cut off, like I was saying."),
        ("inmate", "Tell Rico get rid of the green one, out past the quarry, for real."),
        ("other", "I heard you the first time."),
    ],
    20: [
        ("other", "Baby, you know you didn't come home till after midnight that night, Dre."),
        ("inmate", "Mama, not on the phone."),
        ("other", "I'm just saying what I remember."),
    ],
    24: [
        ("third", "They pulled me over in Ashby last week, just a ticket."),
        ("other", "Rico, you need to slow down for real."),
    ],
    31: [
        ("other", "Mama said the detective called the house."),
        ("inmate", "I wasn't even there that night, ask anybody."),
        ("other", "I'm not the one you gotta convince."),
    ],
    33: [
        ("other", "They asking about some pawn ticket with your name on it."),
        ("inmate", "I just moved the watch for Dre at Lucky's, that's all I did."),
        ("other", "Kevin, you need to stop talking."),
    ],
}


def _fmt_date(rng: random.Random, i: int) -> str:
    # Calls run from July 2018 to February 2019, in order.
    month_starts = [(2018, 7), (2018, 8), (2018, 9), (2018, 10), (2018, 11), (2018, 12), (2019, 1), (2019, 2)]
    y, m = month_starts[min((i - 1) * len(month_starts) // 40, len(month_starts) - 1)]
    return f"{y}-{m:02d}-{rng.randint(1, 28):02d}"


def _make_call(rng: random.Random, i: int) -> dict:
    inmate, other, third = CALL_PARTIES[i]
    who = {"inmate": inmate, "other": other, "third": third}
    duration = rng.randint(120, 360)
    target_lines = max(12, duration // 10)
    filler: list[tuple[str, str]] = []
    for n in range(target_lines):
        if third and rng.random() < 0.15:
            filler.append((third, rng.choice(OTHER_FILLER)))
        elif n % 2 == 0:
            filler.append((inmate, rng.choice(INMATE_FILLER)))
        else:
            filler.append((other, rng.choice(OTHER_FILLER)))
    plant = [(who[role], text) for role, text in PLANTS.get(i, [])]
    pos = rng.randint(2, max(2, len(filler) - 3))
    body = filler[:pos] + plant + filler[pos:]

    # Spread lines over the call's duration with irregular gaps.
    starts = [0]
    t = 6
    for _ in body:
        starts.append(t)
        t += rng.randint(4, 12)
    duration = max(duration, t)
    entries = [(SYSTEM, SYSTEM_LINE)] + body
    lines = []
    for idx, (speaker, text) in enumerate(entries):
        start = starts[idx]
        end = (starts[idx + 1] - 1) if idx + 1 < len(starts) else duration
        lines.append({"start_ts": start, "end_ts": max(start, end), "speaker": speaker, "text": text})
    participants = [p for p in (inmate, other, third) if p]
    return {
        "call_id": f"CALL-{i:03d}",
        "date": _fmt_date(rng, i),
        "facility": "Merritt County Jail",
        "inmate": inmate,
        "participants": participants,
        "duration": duration,
        "lines": lines,
    }


def _header(title: str, page: int, pages: int) -> list[str]:
    return ["HARLOW CREEK POLICE DEPARTMENT", f"Case No. 09-0314-H    {title}    Page {page} of {pages}"]


# doc_id, title, doc_type, speaker (author or declarant), date, pages (content lines only)
DOCS: list[tuple[str, str, str, str, str, list[list[str]]]] = [
    ("DOC-01", "Incident Report", "incident_report", "Ofc. Dana Marsh", "2009-03-15", [[
        "Reporting officer: Ofc. Dana Marsh, Badge 2217.",
        "Location: Quick Stop Market, 418 Route 9, Harlow Creek.",
        "Date of incident: 03/14/2009.",
        "Dispatch received the 911 call at 2342 hours on 03/14/2009.",
        "Caller was a passing motorist who saw the front door standing open.",
        "On arrival I found the clerk, Marcus Bell, on the floor behind the counter.",
        "Bell was unresponsive and had an apparent gunshot wound to the chest.",
        "Harlow Creek Fire Rescue pronounced Bell deceased at 2358 hours.",
        "The register drawer was open and empty.",
        "The scene was secured and Det. Renee Okafor was notified.",
    ], [
        "Store manager Hector Ruiz arrived at 0040 hours on 03/15/2009.",
        "Ruiz stated approximately $1,260 in cash was taken from the register.",
        "Ruiz stated the victim always wore a gold Seiko wristwatch.",
        "No watch was found on the victim or at the scene.",
        "A red baseball cap was located near the front door and collected.",
        "One spent shell casing was located near the register counter.",
        "Neighborhood canvass was started at 0115 hours.",
        "See witness statements DOC-03 and DOC-04 and evidence log DOC-05.",
    ]]),
    ("DOC-02", "Witness Statement - Hector Ruiz", "witness_statement", "Hector Ruiz", "2009-03-15", [[
        "I am the manager of the Quick Stop Market on Route 9.",
        "Marcus Bell worked the night shift alone on weekends.",
        "Marcus closed out the register at 2300 hours most nights and kept the drop safe locked.",
        "He had worked for me for about four years and never had a problem with anyone.",
        "I counted the safe and it was not opened.",
        "The cash taken was from the register only.",
        "Marcus wore his gold watch every day, it was from his father.",
        "I signed this statement on 03/15/2009.",
    ]]),
    ("DOC-03", "Witness Statement - Gloria Fenn", "witness_statement", "Gloria Fenn", "2009-03-15", [[
        "I live across Route 9 from the Quick Stop, on the second floor.",
        "At about 11:40 at night I heard a loud bang, like a firecracker.",
        "I went to the window and looked at the store lot.",
        "I saw a dark green car pull out of the lot with no headlights on.",
        "The car was dark green, I am sure of the color.",
        "It went east on Route 9 toward Dunmore.",
        "I think there were two people in the car but I could not see faces.",
        "I called my sister before I called anyone else.",
        "I signed this statement on 03/15/2009.",
    ]]),
    ("DOC-04", "Witness Statement - Paul Ortiz", "witness_statement", "Paul Ortiz", "2009-03-16", [[
        "I was walking my dog on Route 9 near the Quick Stop that night.",
        "I heard what sounded like a gunshot from the store.",
        "A vehicle came out of the lot fast and went west toward Ashby.",
        "I am pretty sure it was a blue pickup truck, an older Ford.",
        "The color was blue, I am pretty sure, but it was dark out.",
        "One man was walking away from the store on foot, wearing a hooded sweatshirt.",
        "I did not see where he went.",
        "I signed this statement on 03/16/2009.",
    ]]),
    ("DOC-05", "Evidence Log", "evidence_log", "Evidence Tech S. Varga", "2009-03-15", [[
        "Collected by: Evidence Tech S. Varga.",
        "Date collected: 03/14/2008.",
        "Item 1: register drawer, processed for latent prints.",
        "Item 2: front door handle swab.",
        "Item 3: counter surface swab.",
        "Item 4: red baseball cap, found on floor by the front door.",
        "Item 5: store receipt roll from the register.",
        "Item 6: victim's clothing, collected at the medical examiner's office.",
        "Item 7: one 9mm shell casing, recovered near the register counter.",
        "Item 8: footwear impression photo, front walkway.",
    ], [
        "Chain of custody: all items transferred to the county lab on 03/17/2009.",
        "Item 4 and Item 7 were flagged for priority analysis.",
        "Item 8 photo was printed and placed in the case file.",
        "Log reviewed by Det. Renee Okafor.",
    ]]),
    ("DOC-06", "Supplemental Report - Cold Case Review", "supplemental_report", "Det. Renee Okafor", "2019-03-02", [[
        "This case was reassigned for cold case review on 06/04/2018.",
        "Andre Whitfield and Kevin Lopez were both held at Merritt County Jail on unrelated charges in 2018.",
        "Recorded jail calls from July 2018 to February 2019 were requested and reviewed.",
        "Each call was reviewed by two detectives and logged with call ID and timestamp.",
        "Whitfield is known by the nickname Dre.",
    ], [
        "Lopez was interviewed on 02/20/2019, see DOC-15.",
        "Vehicle records for green sedans in the Dunmore area were requested, see DOC-09.",
        "The pawn record from Lucky's Pawn was located, see DOC-14.",
        "Review is ongoing and no charges have been filed.",
    ]]),
    ("DOC-07", "Witness Statement - Darnell Bell", "witness_statement", "Darnell Bell", "2009-03-17", [[
        "I am the brother of Marcus Bell.",
        "I was at home in Ashby with my wife all night and heard the news the next morning.",
        "Marcus told me a week before that someone had been hanging around the store.",
        "He did not say who it was.",
        "I do not know anyone named Andre or Kevin.",
        "I signed this statement on 03/17/2009.",
    ]]),
    ("DOC-08", "Surveillance Notes", "investigator_notes", "Det. Renee Okafor", "2009-03-18", [[
        "The store had two cameras, one at the front entrance and one at the rear.",
        "The front camera recorded but the lens faced the register, not the lot.",
        "The front footage shows a man in a red cap and hooded sweatshirt at 2338 hours.",
        "His face is not visible in any frame.",
        "The rear camera had not been recording since February due to a failed hard drive.",
        "A copy of the front footage was placed into evidence.",
    ]]),
    ("DOC-09", "Vehicle Registration Check", "records_check", "Det. Renee Okafor", "2018-11-09", [[
        "Records request for green sedans registered in Dunmore and Harlow Creek in 2009.",
        "Forty-one vehicles matched the request.",
        "One 1998 Honda Accord, green, was registered to Enrique Banks (known as Rico) of Dunmore.",
        "Banks is a cousin of Andre Whitfield.",
        "The Accord registration lapsed in 2010 and the vehicle was never located.",
    ]]),
    ("DOC-10", "Canvass Notes", "investigator_notes", "Ofc. Dana Marsh", "2009-03-15", [[
        "Twelve homes on Route 9 were contacted between 0115 and 0300 hours.",
        "Nine residents reported hearing nothing.",
        "Gloria Fenn reported hearing a bang and seeing a vehicle, statement taken.",
        "One resident reported a dog barking at about the same time.",
        "Two homes did not answer and cards were left.",
    ]]),
    ("DOC-11", "Interview Summary - Tasha Greene", "interview_summary", "Tasha Greene", "2009-04-02", [[
        "Tasha Greene was interviewed at the Harlow Creek station.",
        "Greene stated she was dating Andre Whitfield in March 2009.",
        "Greene stated she was at work at the hospital laundry that evening.",
        "Greene stated she did not know where Whitfield was that night.",
        "Greene declined to answer further questions and left.",
    ]]),
    ("DOC-12", "Medical Examiner Summary", "medical_summary", "Dr. L. Hsu", "2009-03-16", [[
        "Decedent: Marcus Bell, age 34.",
        "Cause of death: single gunshot wound to the chest.",
        "Manner of death: homicide.",
        "No defensive wounds were observed.",
        "A pale band of skin on the left wrist suggests a watch was regularly worn.",
    ]]),
    ("DOC-13", "Lab Report", "lab_report", "County Crime Lab", "2009-05-11", [[
        "Item 4 (red baseball cap): hair recovered was insufficient for a full DNA profile.",
        "Item 4: a partial profile was developed and retained for comparison.",
        "Item 7 (shell casing): consistent with a 9mm pistol.",
        "Item 7: no match in the state ballistics database at time of testing.",
        "Item 1: two partial latent prints, not suitable for comparison.",
    ]]),
    ("DOC-14", "Pawn Record - Lucky's Pawn", "records_check", "Det. Renee Okafor", "2018-12-03", [[
        "Records obtained from Lucky's Pawn, 77 Mill Street, Dunmore.",
        "Gold Seiko wristwatch pawned on 03/16/2009 by customer signing as K. Lopez.",
        "Loan amount: $150.",
        "The watch was never redeemed and was sold in June 2009.",
        "The store does not keep ID copies from 2009.",
    ]]),
    ("DOC-15", "Supplemental Report - Interview of Kevin Lopez", "supplemental_report", "Det. Renee Okafor",
     "2019-02-20", [[
        "Kevin Lopez was interviewed at Merritt County Jail with counsel present.",
        "Lopez stated he did not go into the Quick Stop on 03/14/2009.",
        "Lopez stated he did not remember pawning a watch.",
        "Lopez was shown the pawn record and declined to comment.",
        "Lopez stated he wasn't even there that night.",
        "Interview ended after 25 minutes at the request of counsel.",
    ]]),
]


def _make_doc(spec: tuple) -> dict:
    doc_id, title, doc_type, speaker, date, pages = spec
    out_pages = []
    for p, content in enumerate(pages, start=1):
        lines = _header(title, p, len(pages)) + content
        out_pages.append({"page": p, "lines": lines})
    return {
        "doc_id": doc_id, "title": title, "doc_type": doc_type, "speaker": speaker, "date": date,
        "pages": out_pages,
    }


def _ev(source_id: str, contains: str) -> dict:
    return {"source_id": source_id, "contains": contains}


# category: answerable | multi_source | unanswerable. Each evidence group is satisfied by any one of its items.
GOLD = [
    ("What did Andre tell Rico to do with the green car?", "answerable",
     [[_ev("CALL-017", "get rid of the green one"), _ev("CALL-018", "get rid of the green one")]]),
    ("Who did Tasha say had the gold watch?", "answerable",
     [[_ev("CALL-008", "Kev said he took it to Lucky's")]]),
    ("What time did dispatch receive the 911 call?", "answerable",
     [[_ev("DOC-01", "at 2342 hours")]]),
    ("How much cash was taken from the register?", "answerable",
     [[_ev("DOC-01", "$1,260")]]),
    ("What did Gloria Fenn see pull out of the lot?", "answerable",
     [[_ev("DOC-03", "dark green car pull out of the lot")]]),
    ("What vehicle did Paul Ortiz describe?", "answerable",
     [[_ev("DOC-04", "blue pickup truck")]]),
    ("What caliber was the shell casing?", "answerable",
     [[_ev("DOC-05", "9mm shell casing"), _ev("DOC-13", "consistent with a 9mm pistol")]]),
    ("Where was the red baseball cap found?", "answerable",
     [[_ev("DOC-05", "found on floor by the front door"), _ev("DOC-01", "located near the front door")]]),
    ("Did the lab get a DNA profile from the red cap?", "answerable",
     [[_ev("DOC-13", "insufficient for a full DNA profile")]]),
    ("What did Andre say about where he was that night?", "answerable",
     [[_ev("CALL-005", "at my mom's watching the game")]]),
    ("What did Kevin say on the calls about being there that night?", "answerable",
     [[_ev("CALL-031", "I wasn't even there that night")]]),
    ("What did Andre say about the red hat?", "answerable",
     [[_ev("CALL-012", "Rico always wore red")]]),
    ("What did Loretta Whitfield say about that night?", "answerable",
     [[_ev("CALL-020", "after midnight")]]),
    ("What did Kevin say about the watch at Lucky's?", "answerable",
     [[_ev("CALL-033", "moved the watch for Dre")]]),
    ("What did Andre tell Tasha to do if detectives come by?", "answerable",
     [[_ev("CALL-010", "call my lawyer")]]),
    ("Who was the green Honda Accord registered to?", "answerable",
     [[_ev("DOC-09", "registered to Enrique Banks")]]),
    ("Where did Darnell Bell say he was all night?", "answerable",
     [[_ev("DOC-07", "at home in Ashby")]]),
    ("Why was the rear camera not recording?", "answerable",
     [[_ev("DOC-08", "failed hard drive")]]),
    ("When was the case reassigned for cold case review?", "answerable",
     [[_ev("DOC-06", "06/04/2018")]]),
    ("What was the loan amount for the pawned watch?", "answerable",
     [[_ev("DOC-14", "$150")]]),
    ("Where did Andre say he was that night, and what did Loretta say about that night?", "multi_source",
     [[_ev("CALL-005", "at my mom's")], [_ev("CALL-020", "after midnight")]]),
    ("What color was the vehicle according to the witness statements?", "multi_source",
     [[_ev("DOC-03", "dark green")], [_ev("DOC-04", "blue")]]),
    ("Who pawned the gold watch, and what did Kevin say about the watch?", "multi_source",
     [[_ev("DOC-14", "K. Lopez")], [_ev("CALL-033", "moved the watch")]]),
    ("What date is recorded in the incident report, and what date is in the evidence log?", "multi_source",
     [[_ev("DOC-01", "03/14/2009")], [_ev("DOC-05", "03/14/2008")]]),
    ("Who was the green car registered to, and what did Andre tell Rico to do with it?", "multi_source",
     [[_ev("DOC-09", "Enrique Banks (known as Rico)")],
      [_ev("CALL-017", "Tell Rico get rid of the green one"), _ev("CALL-018", "Tell Rico get rid of the green one")]]),
    ("What did the victim's brother say on the jail calls?", "unanswerable", []),
    ("What was the license plate of the green car?", "unanswerable", []),
    ("Who was the getaway driver?", "unanswerable", []),
    ("What did Tasha say about the shell casing?", "unanswerable", []),
    ("What did the security guard see?", "unanswerable", []),
]


def generate(seed: int = SEED) -> dict:
    rng = random.Random(seed)
    calls = [_make_call(rng, i) for i in range(1, 41)]
    docs = [_make_doc(spec) for spec in DOCS]
    gold = [
        {"qid": f"Q{n:02d}", "question": q, "category": cat, "evidence": [{"any_of": g} for g in groups]}
        for n, (q, cat, groups) in enumerate(GOLD, start=1)
    ]
    case = dict(CASE, people=PEOPLE)
    return {"case.json": case, "calls.json": calls, "case_files.json": docs, "gold_questions.json": gold}


def write(out_dir: Path = DATA_DIR, seed: int = SEED) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in generate(seed).items():
        text = json.dumps(payload, indent=1, ensure_ascii=False) + "\n"
        (out_dir / name).write_text(text, encoding="utf-8", newline="\n")
    return out_dir


def ensure_data(out_dir: Path = DATA_DIR) -> Path:
    if not all((out_dir / n).exists() for n in ("case.json", "calls.json", "case_files.json", "gold_questions.json")):
        write(out_dir)
    return out_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the synthetic case data.")
    parser.add_argument("--out", type=Path, default=DATA_DIR)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    path = write(args.out, args.seed)
    print(f"Wrote synthetic case data to {path}")


if __name__ == "__main__":
    main()
