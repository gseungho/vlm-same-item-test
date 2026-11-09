# 상품 사진 쌍을 고른 에이전트에게 준 지시

실험 대상이 아닌 에이전트(Claude Fable 5.1)에게 앵커와 사진 쌍을 고르고, 고른 사진을 1000픽셀로 다시 확인하게 했다. 그때 준 지시를 순서와 문장 그대로 옮겼고, 로컬 폴더 경로만 `<repo>`로 바꿨다. 에이전트가 읽은 입력 파일과 사진은 올리지 않았다.

항목 제목은 에이전트를 부를 때 붙인 작업 이름(영어)이다. 머리 줄의 "에이전트 유형"은 부를 때 지정한 값이고, None은 따로 지정하지 않았다는 뜻이다.

## 0. Select pairs: shoes part 1

시각 2026-11-02T14:40:52.410Z, 모델 fable, 에이전트 유형 None

````text
You are selecting product photos for a study, using only your own eyes on contact sheets. Do not call any API, install anything or run other analysis. You are only to read images and write one JSON file.

Project folder: <repo>
Sheets: data\pairs\sheets\<sheet>.jpg (use the absolute path). Each sheet has 5 rows. Row "A" is the anchor product. Rows "C1" to "C4" are other products of the same brand. Each photo has a small red index (0, 1, 2...) at its top-left. Read several sheets per response to save turns.

For each sheet, choose these or reject the sheet:

- a1: an A photo.
- a2: another A photo of the same physical item, from a clearly different angle (not a near-duplicate or a mirror of a1).
- c_row and c: one photo from one C row, showing a truly different design. It must differ in shape or structure so that a careful person comparing two photos could tell them apart. Do NOT pick a C row that is the same design in another colour or material, the same mould or model, or a set containing the same item. The C product should otherwise look alike: same type of item and, if possible, a comparable colour and style. Prefer the closest C row that is truly different.
- c should be from a viewing angle like a2's, so the a1-a2 pair and the a1-c pair are equally easy to compare on angle.

Every chosen photo must: show the whole product (one item or a pair of the same item); have no person or body; not be a close-up, sole-only view, inside-only view, or packaging shot; have no dimension lines, size charts, added text, or props such as a magazine; show no brand name or logo you can read or make out, including on insoles, tongues, tabs, plates and badges. When a view is likely to show an insole or tag with text (top-down views especially), prefer another view. These are thumbnails, so also avoid photos where a small mark seems present even if you cannot read it.

Reject the sheet (use=false) if no valid set exists, and say why. Do not stretch the rules to keep a sheet.

Write the results to the file named below as a JSON array with one object per sheet, in sheet order:
{"sheet":"s001","use":true,"a1":0,"a2":3,"c_row":3,"c":0,"views":{"a1":"three-quarter","a2":"side","c":"side"},"closeness":"close|medium|far","note":"under 15 words: how c differs, or why rejected"}
Views must be one of: side, three-quarter, front, back, top, pair. For rejected sheets, keep only sheet, use and note. closeness says how alike the C photo looks to a1 overall.

Your output file: data\pairs\pass1_shoes1.json

Your sheets (50): s000 s001 s002 s003 s005 s006 s008 s009 s010 s012 s013 s014 s015 s016 s017 s019 s020 s021 s022 s023 s024 s025 s026 s027 s028 s030 s031 s032 s033 s034 s035 s036 s037 s038 s039 s040 s041 s042 s044 s045 s046 s047 s048 s049 s050 s053 s054 s055 s057 s058

When finished, reply with only: how many sheets you used, how many you rejected, and the most common rejection reasons.
````

## 1. Select pairs: shoes part 2

시각 2026-11-02T14:40:59.963Z, 모델 fable, 에이전트 유형 None

````text
You are selecting product photos for a study, using only your own eyes on contact sheets. Do not call any API, install anything or run other analysis. You are only to read images and write one JSON file.

Project folder: <repo>
Sheets: data\pairs\sheets\<sheet>.jpg (use the absolute path). Each sheet has 5 rows. Row "A" is the anchor product. Rows "C1" to "C4" are other products of the same brand. Each photo has a small red index (0, 1, 2...) at its top-left. Read several sheets per response to save turns.

For each sheet, choose these or reject the sheet:

- a1: an A photo.
- a2: another A photo of the same physical item, from a clearly different angle (not a near-duplicate or a mirror of a1).
- c_row and c: one photo from one C row, showing a truly different design. It must differ in shape or structure so that a careful person comparing two photos could tell them apart. Do NOT pick a C row that is the same design in another colour or material, the same mould or model, or a set containing the same item. The C product should otherwise look alike: same type of item and, if possible, a comparable colour and style. Prefer the closest C row that is truly different.
- c should be from a viewing angle like a2's, so the a1-a2 pair and the a1-c pair are equally easy to compare on angle.

Every chosen photo must: show the whole product (one item or a pair of the same item); have no person or body; not be a close-up, sole-only view, inside-only view, or packaging shot; have no dimension lines, size charts, added text, or props such as a magazine; show no brand name or logo you can read or make out, including on insoles, tongues, tabs, plates and badges. When a view is likely to show an insole or tag with text (top-down views especially), prefer another view. These are thumbnails, so also avoid photos where a small mark seems present even if you cannot read it.

Reject the sheet (use=false) if no valid set exists, and say why. Do not stretch the rules to keep a sheet.

Write the results to the file named below as a JSON array with one object per sheet, in sheet order:
{"sheet":"s001","use":true,"a1":0,"a2":3,"c_row":3,"c":0,"views":{"a1":"three-quarter","a2":"side","c":"side"},"closeness":"close|medium|far","note":"under 15 words: how c differs, or why rejected"}
Views must be one of: side, three-quarter, front, back, top, pair. For rejected sheets, keep only sheet, use and note. closeness says how alike the C photo looks to a1 overall.

Your output file: data\pairs\pass1_shoes2.json

Your sheets (50): s059 s060 s062 s063 s064 s067 s068 s069 s070 s071 s072 s073 s074 s075 s076 s077 s078 s079 s081 s082 s083 s085 s086 s087 s088 s089 s090 s091 s092 s093 s094 s095 s096 s097 s098 s100 s101 s102 s103 s104 s105 s106 s107 s108 s109 s110 s111 s112 s113 s114

When finished, reply with only: how many sheets you used, how many you rejected, and the most common rejection reasons.
````

## 2. Select pairs: bags and luggage

시각 2026-11-02T14:41:07.561Z, 모델 fable, 에이전트 유형 None

````text
You are selecting product photos for a study, using only your own eyes on contact sheets. Do not call any API, install anything or run other analysis. You are only to read images and write one JSON file.

Project folder: <repo>
Sheets: data\pairs\sheets\<sheet>.jpg (use the absolute path). Each sheet has 5 rows. Row "A" is the anchor product. Rows "C1" to "C4" are other products of the same brand. Each photo has a small red index (0, 1, 2...) at its top-left. Read several sheets per response to save turns.

For each sheet, choose these or reject the sheet:

- a1: an A photo.
- a2: another A photo of the same physical item, from a clearly different angle (not a near-duplicate or a mirror of a1).
- c_row and c: one photo from one C row, showing a truly different design. It must differ in shape or structure so that a careful person comparing two photos could tell them apart. Do NOT pick a C row that is the same design in another colour or material, the same mould or model, or a set containing the same item. The C product should otherwise look alike: same type of item and, if possible, a comparable colour and style. Prefer the closest C row that is truly different.
- c should be from a viewing angle like a2's, so the a1-a2 pair and the a1-c pair are equally easy to compare on angle.

Every chosen photo must: show the whole product; have no person or body; not be a close-up, inside-only view, or packaging shot; have no dimension lines, size charts, added text, or props such as a magazine; show no brand name or logo you can read or make out, including on plates, tabs, badges, patches, zip pulls and embossing. These are thumbnails, so also avoid photos where a small mark seems present even if you cannot read it.

Reject the sheet (use=false) if no valid set exists, and say why. Do not stretch the rules to keep a sheet.

Write the results to the file named below as a JSON array with one object per sheet, in sheet order:
{"sheet":"s001","use":true,"a1":0,"a2":3,"c_row":3,"c":0,"views":{"a1":"three-quarter","a2":"side","c":"side"},"closeness":"close|medium|far","note":"under 15 words: how c differs, or why rejected"}
Views must be one of: side, three-quarter, front, back, top, pair. For rejected sheets, keep only sheet, use and note. closeness says how alike the C photo looks to a1 overall.

Your output file: data\pairs\pass1_bags.json

Your sheets (54): s004 s018 s043 s051 s052 s056 s061 s084 s099 s115 s116 s117 s118 s119 s120 s123 s125 s127 s130 s132 s134 s136 s137 s139 s140 s141 s142 s143 s144 s146 s007 s065 s128 s133 s135 s138 s145 s147 s148 s149 s156 s158 s126 s131 s153 s157 s159 s162 s164 s165 s168 s169 s170 s171

When finished, reply with only: how many sheets you used, how many you rejected, and the most common rejection reasons.
````

## 3. Select pairs: boots and sandals

시각 2026-11-02T14:41:15.583Z, 모델 fable, 에이전트 유형 None

````text
You are selecting product photos for a study, using only your own eyes on contact sheets. Do not call any API, install anything or run other analysis. You are only to read images and write one JSON file.

Project folder: <repo>
Sheets: data\pairs\sheets\<sheet>.jpg (use the absolute path). Each sheet has 5 rows. Row "A" is the anchor product. Rows "C1" to "C4" are other products of the same brand. Each photo has a small red index (0, 1, 2...) at its top-left. Read several sheets per response to save turns.

For each sheet, choose these or reject the sheet:

- a1: an A photo.
- a2: another A photo of the same physical item, from a clearly different angle (not a near-duplicate or a mirror of a1).
- c_row and c: one photo from one C row, showing a truly different design. It must differ in shape or structure so that a careful person comparing two photos could tell them apart. Do NOT pick a C row that is the same design in another colour or material, the same mould or model, or a set containing the same item. The C product should otherwise look alike: same type of item and, if possible, a comparable colour and style. Prefer the closest C row that is truly different.
- c should be from a viewing angle like a2's, so the a1-a2 pair and the a1-c pair are equally easy to compare on angle.

Every chosen photo must: show the whole product (one item or a pair of the same item); have no person or body; not be a close-up, sole-only view, inside-only view, or packaging shot; have no dimension lines, size charts, added text, or props such as a magazine; show no brand name or logo you can read or make out, including on insoles, footbeds, straps, tabs, plates and badges. Sandals and open footwear often show text on the footbed in top-down or angled views, so prefer plain side or back views. These are thumbnails, so also avoid photos where a small mark seems present even if you cannot read it.

Reject the sheet (use=false) if no valid set exists, and say why. Do not stretch the rules to keep a sheet.

Write the results to the file named below as a JSON array with one object per sheet, in sheet order:
{"sheet":"s001","use":true,"a1":0,"a2":3,"c_row":3,"c":0,"views":{"a1":"three-quarter","a2":"side","c":"side"},"closeness":"close|medium|far","note":"under 15 words: how c differs, or why rejected"}
Views must be one of: side, three-quarter, front, back, top, pair. For rejected sheets, keep only sheet, use and note. closeness says how alike the C photo looks to a1 overall.

Your output file: data\pairs\pass1_boots.json

Your sheets (50): s011 s029 s066 s080 s122 s124 s129 s150 s152 s160 s163 s166 s167 s174 s175 s176 s177 s178 s181 s183 s187 s189 s191 s194 s195 s121 s151 s154 s155 s161 s172 s173 s179 s180 s182 s184 s185 s186 s188 s190 s192 s193 s196 s197 s198 s199 s200 s201 s202 s203

When finished, reply with only: how many sheets you used, how many you rejected, and the most common rejection reasons.
````

## 4. Select pairs: second round part 1

시각 2026-11-02T14:52:09.743Z, 모델 fable, 에이전트 유형 None

````text
You are selecting product photos for a study, using only your own eyes on contact sheets. Do not call any API, install anything or run other analysis. You are only to read images and write one JSON file.

Project folder: <repo>
Sheets: data\pairs\sheets\<sheet>.jpg (use the absolute path). Each sheet has up to 5 rows. Row "A" is the anchor product. Rows "C1" to "C4" are other products of the same brand. Each photo has a small red index (0, 1, 2...) at its top-left. Read several sheets per response to save turns.

For each sheet, choose these or reject the sheet:

- a1: an A photo.
- a2: another A photo of the same physical item, from a clearly different angle (not a near-duplicate or a mirror of a1).
- c_row and c: one photo from one C row, showing a truly different design. It must differ in shape or structure so that a careful person comparing two photos could tell them apart. Do NOT pick a C row that is the same design in another colour or material, the same mould or model, or a set containing the same item. The C product should otherwise look alike: same type of item and, if possible, a comparable colour and style. Prefer the closest C row that is truly different.
- c should be from a viewing angle like a2's, so the a1-a2 pair and the a1-c pair are equally easy to compare on angle.

Every chosen photo must: show the whole product (one item or a pair of the same item); have no person or body; not be a close-up, sole-only view, inside-only view, or packaging shot; have no dimension lines, size charts, added text, or props such as a magazine; show no brand name or logo you can read or make out, including on insoles, footbeds, tongues, straps, tabs, plates, badges, patches, zip pulls and embossing. When a view is likely to show an insole or tag with text (top-down views especially), prefer another view. These are thumbnails, so also avoid photos where a small mark seems present even if you cannot read it.

Reject the sheet (use=false) if no valid set exists, and say why. Do not stretch the rules to keep a sheet.

Write the results to the file named below as a JSON array with one object per sheet, in sheet order:
{"sheet":"s001","use":true,"a1":0,"a2":3,"c_row":3,"c":0,"views":{"a1":"three-quarter","a2":"side","c":"side"},"closeness":"close|medium|far","note":"under 15 words: how c differs, or why rejected"}
Views must be one of: side, three-quarter, front, back, top, pair. For rejected sheets, keep only sheet, use and note. closeness says how alike the C photo looks to a1 overall.

Your output file: data\pairs\pass1_more1.json

Your sheets (40): s204 s205 s206 s207 s208 s209 s210 s211 s212 s213 s214 s215 s216 s217 s218 s219 s220 s221 s222 s223 s224 s225 s226 s227 s228 s229 s230 s231 s232 s233 s234 s235 s236 s237 s238 s239 s240 s241 s242 s243

When finished, reply with only: how many sheets you used, how many you rejected, and the most common rejection reasons.
````

## 5. Select pairs: second round part 2

시각 2026-11-02T14:52:17.150Z, 모델 fable, 에이전트 유형 None

````text
You are selecting product photos for a study, using only your own eyes on contact sheets. Do not call any API, install anything or run other analysis. You are only to read images and write one JSON file.

Project folder: <repo>
Sheets: data\pairs\sheets\<sheet>.jpg (use the absolute path). Each sheet has up to 5 rows. Row "A" is the anchor product. Rows "C1" to "C4" are other products of the same brand. Each photo has a small red index (0, 1, 2...) at its top-left. Read several sheets per response to save turns.

For each sheet, choose these or reject the sheet:

- a1: an A photo.
- a2: another A photo of the same physical item, from a clearly different angle (not a near-duplicate or a mirror of a1).
- c_row and c: one photo from one C row, showing a truly different design. It must differ in shape or structure so that a careful person comparing two photos could tell them apart. Do NOT pick a C row that is the same design in another colour or material, the same mould or model, or a set containing the same item. The C product should otherwise look alike: same type of item and, if possible, a comparable colour and style. Prefer the closest C row that is truly different.
- c should be from a viewing angle like a2's, so the a1-a2 pair and the a1-c pair are equally easy to compare on angle.

Every chosen photo must: show the whole product (one item or a pair of the same item); have no person or body; not be a close-up, sole-only view, inside-only view, or packaging shot; have no dimension lines, size charts, added text, or props such as a magazine; show no brand name or logo you can read or make out, including on insoles, footbeds, tongues, straps, tabs, plates, badges, patches, zip pulls and embossing. When a view is likely to show an insole or tag with text (top-down views especially), prefer another view. These are thumbnails, so also avoid photos where a small mark seems present even if you cannot read it.

Reject the sheet (use=false) if no valid set exists, and say why. Do not stretch the rules to keep a sheet.

Write the results to the file named below as a JSON array with one object per sheet, in sheet order:
{"sheet":"s001","use":true,"a1":0,"a2":3,"c_row":3,"c":0,"views":{"a1":"three-quarter","a2":"side","c":"side"},"closeness":"close|medium|far","note":"under 15 words: how c differs, or why rejected"}
Views must be one of: side, three-quarter, front, back, top, pair. For rejected sheets, keep only sheet, use and note. closeness says how alike the C photo looks to a1 overall.

Your output file: data\pairs\pass1_more2.json

Your sheets (40): s244 s245 s246 s247 s248 s249 s250 s251 s252 s253 s254 s255 s256 s257 s258 s259 s260 s261 s262 s263 s264 s265 s266 s267 s268 s269 s270 s271 s272 s273 s274 s275 s276 s277 s278 s279 s280 s281 s282 s283

When finished, reply with only: how many sheets you used, how many you rejected, and the most common rejection reasons.
````

## 6. Select pairs: second round part 3

시각 2026-11-02T14:52:24.524Z, 모델 fable, 에이전트 유형 None

````text
You are selecting product photos for a study, using only your own eyes on contact sheets. Do not call any API, install anything or run other analysis. You are only to read images and write one JSON file.

Project folder: <repo>
Sheets: data\pairs\sheets\<sheet>.jpg (use the absolute path). Each sheet has up to 5 rows. Row "A" is the anchor product. Rows "C1" to "C4" are other products of the same brand. Each photo has a small red index (0, 1, 2...) at its top-left. Read several sheets per response to save turns.

For each sheet, choose these or reject the sheet:

- a1: an A photo.
- a2: another A photo of the same physical item, from a clearly different angle (not a near-duplicate or a mirror of a1).
- c_row and c: one photo from one C row, showing a truly different design. It must differ in shape or structure so that a careful person comparing two photos could tell them apart. Do NOT pick a C row that is the same design in another colour or material, the same mould or model, or a set containing the same item. The C product should otherwise look alike: same type of item and, if possible, a comparable colour and style. Prefer the closest C row that is truly different.
- c should be from a viewing angle like a2's, so the a1-a2 pair and the a1-c pair are equally easy to compare on angle.

Every chosen photo must: show the whole product (one item or a pair of the same item); have no person or body; not be a close-up, sole-only view, inside-only view, or packaging shot; have no dimension lines, size charts, added text, or props such as a magazine; show no brand name or logo you can read or make out, including on insoles, footbeds, tongues, straps, tabs, plates, badges, patches, zip pulls and embossing. When a view is likely to show an insole or tag with text (top-down views especially), prefer another view. These are thumbnails, so also avoid photos where a small mark seems present even if you cannot read it.

Reject the sheet (use=false) if no valid set exists, and say why. Do not stretch the rules to keep a sheet.

Write the results to the file named below as a JSON array with one object per sheet, in sheet order:
{"sheet":"s001","use":true,"a1":0,"a2":3,"c_row":3,"c":0,"views":{"a1":"three-quarter","a2":"side","c":"side"},"closeness":"close|medium|far","note":"under 15 words: how c differs, or why rejected"}
Views must be one of: side, three-quarter, front, back, top, pair. For rejected sheets, keep only sheet, use and note. closeness says how alike the C photo looks to a1 overall.

Your output file: data\pairs\pass1_more3.json

Your sheets (38): s284 s285 s286 s287 s288 s289 s290 s291 s292 s293 s294 s295 s296 s297 s298 s299 s300 s301 s302 s303 s304 s305 s306 s307 s308 s309 s310 s311 s312 s313 s314 s315 s316 s317 s318 s319 s320 s321

When finished, reply with only: how many sheets you used, how many you rejected, and the most common rejection reasons.
````

## 7. Check photos at 1000px part 1

시각 2026-11-02T15:00:29.332Z, 모델 fable, 에이전트 유형 None

````text
You are checking product photos for a study, using only your own eyes. Do not call any API, install anything or run other analysis. You are only to read images and write one JSON file.

Project folder: <repo>
Your list: data\pairs\check_part1.txt. Each line is one set: `<sheet> a1=<id> a2=<id> c=<id>`. Each photo is at data\pairs\photos\<id>.jpg (absolute path, 1000 pixels on the long side). Read all three photos of several sets in each response to save turns. Look at each photo at this full size.

Keep a set (ok=true) only if all of these hold:

1. No mark on any of the three photos. A mark is any letter, word, number, monogram or logo on the product or on a tag, whether printed, stamped, embossed, moulded or sewn, however small, even if you cannot read it. Look closely at insoles, footbeds, tongues, heels, soles, straps, side tabs, buckles, plates, zip pulls and hang tags. Plain unmarked hardware, plain rivets and plain stitching are not marks.
2. a1 and a2 show the same physical item: same design, same colour, same details.
3. c shows a truly different design from a1: shape or structure differs so that a careful person comparing the two photos could tell them apart. It is not the same design in another colour or material, and not the same mould or base with only an ornament changed.
4. Each photo shows the whole product with no person, no added text or dimension lines, no props, and is not a close-up.

Apply the same standard to every set. Do not stretch the rules to keep a set, and do not reject a set for anything other than these four rules.

Write the results to data\pairs\pass2_part1.json as a JSON array with one object per line of your list, in list order:
{"sheet":"s000","ok":true,"failed":[],"marks":{"a1":"","a2":"","c":""},"note":"under 15 words"}
`failed` lists the rule numbers that failed. In `marks`, briefly say what you saw and where on that photo, or leave it empty. `note` says how c differs from a1 if ok, or why the set failed.

When finished, reply with only: how many sets you kept, how many you rejected, and how many rejections fell under each rule.
````

## 8. Check photos at 1000px part 2

시각 2026-11-02T15:00:34.797Z, 모델 fable, 에이전트 유형 None

````text
You are checking product photos for a study, using only your own eyes. Do not call any API, install anything or run other analysis. You are only to read images and write one JSON file.

Project folder: <repo>
Your list: data\pairs\check_part2.txt. Each line is one set: `<sheet> a1=<id> a2=<id> c=<id>`. Each photo is at data\pairs\photos\<id>.jpg (absolute path, 1000 pixels on the long side). Read all three photos of several sets in each response to save turns. Look at each photo at this full size.

Keep a set (ok=true) only if all of these hold:

1. No mark on any of the three photos. A mark is any letter, word, number, monogram or logo on the product or on a tag, whether printed, stamped, embossed, moulded or sewn, however small, even if you cannot read it. Look closely at insoles, footbeds, tongues, heels, soles, straps, side tabs, buckles, plates, zip pulls and hang tags. Plain unmarked hardware, plain rivets and plain stitching are not marks.
2. a1 and a2 show the same physical item: same design, same colour, same details.
3. c shows a truly different design from a1: shape or structure differs so that a careful person comparing the two photos could tell them apart. It is not the same design in another colour or material, and not the same mould or base with only an ornament changed.
4. Each photo shows the whole product with no person, no added text or dimension lines, no props, and is not a close-up.

Apply the same standard to every set. Do not stretch the rules to keep a set, and do not reject a set for anything other than these four rules.

Write the results to data\pairs\pass2_part2.json as a JSON array with one object per line of your list, in list order:
{"sheet":"s000","ok":true,"failed":[],"marks":{"a1":"","a2":"","c":""},"note":"under 15 words"}
`failed` lists the rule numbers that failed. In `marks`, briefly say what you saw and where on that photo, or leave it empty. `note` says how c differs from a1 if ok, or why the set failed.

When finished, reply with only: how many sets you kept, how many you rejected, and how many rejections fell under each rule.
````

## 9. Check photos at 1000px part 3

시각 2026-11-02T15:00:40.099Z, 모델 fable, 에이전트 유형 None

````text
You are checking product photos for a study, using only your own eyes. Do not call any API, install anything or run other analysis. You are only to read images and write one JSON file.

Project folder: <repo>
Your list: data\pairs\check_part3.txt. Each line is one set: `<sheet> a1=<id> a2=<id> c=<id>`. Each photo is at data\pairs\photos\<id>.jpg (absolute path, 1000 pixels on the long side). Read all three photos of several sets in each response to save turns. Look at each photo at this full size.

Keep a set (ok=true) only if all of these hold:

1. No mark on any of the three photos. A mark is any letter, word, number, monogram or logo on the product or on a tag, whether printed, stamped, embossed, moulded or sewn, however small, even if you cannot read it. Look closely at insoles, footbeds, tongues, heels, soles, straps, side tabs, buckles, plates, zip pulls and hang tags. Plain unmarked hardware, plain rivets and plain stitching are not marks.
2. a1 and a2 show the same physical item: same design, same colour, same details.
3. c shows a truly different design from a1: shape or structure differs so that a careful person comparing the two photos could tell them apart. It is not the same design in another colour or material, and not the same mould or base with only an ornament changed.
4. Each photo shows the whole product with no person, no added text or dimension lines, no props, and is not a close-up.

Apply the same standard to every set. Do not stretch the rules to keep a set, and do not reject a set for anything other than these four rules.

Write the results to data\pairs\pass2_part3.json as a JSON array with one object per line of your list, in list order:
{"sheet":"s000","ok":true,"failed":[],"marks":{"a1":"","a2":"","c":""},"note":"under 15 words"}
`failed` lists the rule numbers that failed. In `marks`, briefly say what you saw and where on that photo, or leave it empty. `note` says how c differs from a1 if ok, or why the set failed.

When finished, reply with only: how many sets you kept, how many you rejected, and how many rejections fell under each rule.
````

## 10. Rescue sets by swapping photos 1

시각 2026-11-02T15:11:06.706Z, 모델 fable, 에이전트 유형 None

````text
You are checking product photos for a study, using only your own eyes. Do not call any API, install anything or run other analysis. You are only to read images and write one JSON file.

Project folder: <repo>
Your list: data\pairs\rescue_part1.txt. Each line is one set of three photo slots, a1, a2 and c, where one slot's photo was rejected for showing a brand mark. The format is:
`<sheet> replace=<slot> rejected=<id> <the two kept slots as slot=id> options=<id,id,...>`
Each photo is at data\pairs\photos\<id>.jpg (absolute path, 1000 pixels on the long side). For each set, read the two kept photos and the options. Read several photos in each response to save turns.

Meaning of the slots: a1 and a2 are two photos of one product. c is a photo of a different product of the same brand that looks alike.

Pick the one option that can fill the empty slot, or reject the set. The filled set must meet all of these:

1. No mark on any of the three photos, including the kept ones. A mark is any letter, word, number, monogram or logo on the product or on a tag, whether printed, stamped, embossed, moulded or sewn, however small, even if you cannot read it. Look closely at insoles, footbeds, tongues, heels, soles, straps, side tabs, buckles, plates, zip pulls and hang tags. Plain unmarked hardware, plain rivets and plain stitching are not marks.
2. a1 and a2 show the same physical item: same design, same colour, same details, from clearly different angles (not a near-duplicate or a mirror).
3. c shows a truly different design from a1: shape or structure differs so that a careful person comparing the two photos could tell them apart. It is not the same design in another colour or material, and not the same mould or base with only an ornament changed.
4. Each photo shows the whole product (one item or a pair of the same item) with no person, no added text or dimension lines, no props, and is not a close-up, sole-only or inside-only view.
5. c is from a viewing angle like a2's, so the a1-a2 pair and the a1-c pair are equally easy to compare on angle.

If several options qualify, take the one that best meets rule 5. Do not stretch the rules to keep a set.

Write the results to data\pairs\pass3_part1.json as a JSON array with one object per line of your list, in list order:
{"sheet":"s000","ok":true,"slot":"a1","photo":"<chosen option id>","views":{"a1":"side","a2":"side","c":"side"},"failed":[],"marks":{"a1":"","a2":"","c":""},"note":"under 15 words"}
Views must be one of: side, three-quarter, front, back, top, pair. If ok is false, set photo to "" and list the failed rule numbers. In `marks`, briefly say what you saw and where, or leave it empty. `note` says how c differs from a1 if ok, or why the set failed.

When finished, reply with only: how many sets you kept, how many you rejected, and how many rejections fell under each rule.
````

## 11. Rescue sets by swapping photos 2

시각 2026-11-02T15:11:13.794Z, 모델 fable, 에이전트 유형 None

````text
You are checking product photos for a study, using only your own eyes. Do not call any API, install anything or run other analysis. You are only to read images and write one JSON file.

Project folder: <repo>
Your list: data\pairs\rescue_part2.txt. Each line is one set of three photo slots, a1, a2 and c, where one slot's photo was rejected for showing a brand mark. The format is:
`<sheet> replace=<slot> rejected=<id> <the two kept slots as slot=id> options=<id,id,...>`
Each photo is at data\pairs\photos\<id>.jpg (absolute path, 1000 pixels on the long side). For each set, read the two kept photos and the options. Read several photos in each response to save turns.

Meaning of the slots: a1 and a2 are two photos of one product. c is a photo of a different product of the same brand that looks alike.

Pick the one option that can fill the empty slot, or reject the set. The filled set must meet all of these:

1. No mark on any of the three photos, including the kept ones. A mark is any letter, word, number, monogram or logo on the product or on a tag, whether printed, stamped, embossed, moulded or sewn, however small, even if you cannot read it. Look closely at insoles, footbeds, tongues, heels, soles, straps, side tabs, buckles, plates, zip pulls and hang tags. Plain unmarked hardware, plain rivets and plain stitching are not marks.
2. a1 and a2 show the same physical item: same design, same colour, same details, from clearly different angles (not a near-duplicate or a mirror).
3. c shows a truly different design from a1: shape or structure differs so that a careful person comparing the two photos could tell them apart. It is not the same design in another colour or material, and not the same mould or base with only an ornament changed.
4. Each photo shows the whole product (one item or a pair of the same item) with no person, no added text or dimension lines, no props, and is not a close-up, sole-only or inside-only view.
5. c is from a viewing angle like a2's, so the a1-a2 pair and the a1-c pair are equally easy to compare on angle.

If several options qualify, take the one that best meets rule 5. Do not stretch the rules to keep a set.

Write the results to data\pairs\pass3_part2.json as a JSON array with one object per line of your list, in list order:
{"sheet":"s000","ok":true,"slot":"a1","photo":"<chosen option id>","views":{"a1":"side","a2":"side","c":"side"},"failed":[],"marks":{"a1":"","a2":"","c":""},"note":"under 15 words"}
Views must be one of: side, three-quarter, front, back, top, pair. If ok is false, set photo to "" and list the failed rule numbers. In `marks`, briefly say what you saw and where, or leave it empty. `note` says how c differs from a1 if ok, or why the set failed.

When finished, reply with only: how many sets you kept, how many you rejected, and how many rejections fell under each rule.
````

## 12. Check unchecked sets at 1000px

시각 2026-11-02T15:11:19.324Z, 모델 fable, 에이전트 유형 None

````text
You are checking product photos for a study, using only your own eyes. Do not call any API, install anything or run other analysis. You are only to read images and write one JSON file.

Project folder: <repo>
Your list: data\pairs\check_part4.txt. Each line is one set: `<sheet> a1=<id> a2=<id> c=<id>`. Each photo is at data\pairs\photos\<id>.jpg (absolute path, 1000 pixels on the long side). Read all three photos of several sets in each response to save turns. Look at each photo at this full size.

Keep a set (ok=true) only if all of these hold:

1. No mark on any of the three photos. A mark is any letter, word, number, monogram or logo on the product or on a tag, whether printed, stamped, embossed, moulded or sewn, however small, even if you cannot read it. Look closely at insoles, footbeds, tongues, heels, soles, straps, side tabs, buckles, plates, zip pulls and hang tags. Plain unmarked hardware, plain rivets and plain stitching are not marks.
2. a1 and a2 show the same physical item: same design, same colour, same details.
3. c shows a truly different design from a1: shape or structure differs so that a careful person comparing the two photos could tell them apart. It is not the same design in another colour or material, and not the same mould or base with only an ornament changed.
4. Each photo shows the whole product with no person, no added text or dimension lines, no props, and is not a close-up.

Apply the same standard to every set. Do not stretch the rules to keep a set, and do not reject a set for anything other than these four rules.

Write the results to data\pairs\pass2_part4.json as a JSON array with one object per line of your list, in list order:
{"sheet":"s000","ok":true,"failed":[],"marks":{"a1":"","a2":"","c":""},"note":"under 15 words"}
`failed` lists the rule numbers that failed. In `marks`, briefly say what you saw and where on that photo, or leave it empty. `note` says how c differs from a1 if ok, or why the set failed.

When finished, reply with only: how many sets you kept, how many you rejected, and how many rejections fell under each rule.
````

## 13. Select pairs: fashion part 1

시각 2026-11-04T00:46:06.095Z, 모델 fable, 에이전트 유형 general-purpose

````text
You are selecting product photos for a study, using only your own eyes on contact sheets. Do not call any API, install anything or run other analysis. You are only to read images and write one JSON file.

Project folder: <repo>
Sheets: data\confirm\fashion\sheets\<sheet>.jpg (use the absolute path). Each sheet has 5 rows. Row "A" is the anchor product. Rows "C1" to "C4" are other products of the same brand. Each photo has a small red index (0, 1, 2...) at its top-left. A blank cell means a photo failed to load; ignore it. Read several sheets per response to save turns.

For each sheet, choose these or reject the sheet:

- a1: an A photo.
- a2: another A photo of the same physical item, from a clearly different angle (not a near-duplicate or a mirror of a1).
- c_row and c: one photo from one C row, showing a truly different design. It must differ in shape or structure so that a careful person comparing two photos could tell them apart. Do NOT pick a C row that is the same design in another colour or material, the same mould or model, or a set containing the same item. The C product should otherwise look alike: same type of item and, if possible, a comparable colour and style. Prefer the closest C row that is truly different.
- c should be from a viewing angle like a2's, so the a1-a2 pair and the a1-c pair are equally easy to compare on angle.

Every chosen photo must: show the whole product (one item or a pair of the same item); have no person or body; not be a close-up, sole-only view, inside-only view, or packaging shot; have no dimension lines, size charts, added text, or props such as a magazine; show no brand name or logo you can read or make out, including on insoles, tongues, tabs, plates and badges. When a view is likely to show an insole or tag with text (top-down views especially), prefer another view. These are thumbnails, so also avoid photos where a small mark seems present even if you cannot read it.

Reject the sheet (use=false) if no valid set exists, and say why. Do not stretch the rules to keep a sheet.

Write the results to the file named below as a JSON array with one object per sheet, in sheet order:
{"sheet":"f001","use":true,"a1":0,"a2":3,"c_row":3,"c":0,"views":{"a1":"three-quarter","a2":"side","c":"side"},"closeness":"close|medium|far","note":"under 15 words: how c differs, or why rejected"}
Views must be one of: side, three-quarter, front, back, top, pair. For rejected sheets, keep only sheet, use and note. closeness says how alike the C photo looks to a1 overall.

Your output file: data\confirm\fashion\pass1_part1.json

Your sheets (52): f000 to f051, every number in between.

When finished, reply with only: how many sheets you used, how many you rejected, and the most common rejection reasons.
````

## 14. Select pairs: fashion part 2

시각 2026-11-04T00:46:13.090Z, 모델 fable, 에이전트 유형 general-purpose

````text
You are selecting product photos for a study, using only your own eyes on contact sheets. Do not call any API, install anything or run other analysis. You are only to read images and write one JSON file.

Project folder: <repo>
Sheets: data\confirm\fashion\sheets\<sheet>.jpg (use the absolute path). Each sheet has 5 rows. Row "A" is the anchor product. Rows "C1" to "C4" are other products of the same brand. Each photo has a small red index (0, 1, 2...) at its top-left. A blank cell means a photo failed to load; ignore it. Read several sheets per response to save turns.

For each sheet, choose these or reject the sheet:

- a1: an A photo.
- a2: another A photo of the same physical item, from a clearly different angle (not a near-duplicate or a mirror of a1).
- c_row and c: one photo from one C row, showing a truly different design. It must differ in shape or structure so that a careful person comparing two photos could tell them apart. Do NOT pick a C row that is the same design in another colour or material, the same mould or model, or a set containing the same item. The C product should otherwise look alike: same type of item and, if possible, a comparable colour and style. Prefer the closest C row that is truly different.
- c should be from a viewing angle like a2's, so the a1-a2 pair and the a1-c pair are equally easy to compare on angle.

Every chosen photo must: show the whole product (one item or a pair of the same item); have no person or body; not be a close-up, sole-only view, inside-only view, or packaging shot; have no dimension lines, size charts, added text, or props such as a magazine; show no brand name or logo you can read or make out, including on insoles, tongues, tabs, plates and badges. When a view is likely to show an insole or tag with text (top-down views especially), prefer another view. These are thumbnails, so also avoid photos where a small mark seems present even if you cannot read it.

Reject the sheet (use=false) if no valid set exists, and say why. Do not stretch the rules to keep a sheet.

Write the results to the file named below as a JSON array with one object per sheet, in sheet order:
{"sheet":"f053","use":true,"a1":0,"a2":3,"c_row":3,"c":0,"views":{"a1":"three-quarter","a2":"side","c":"side"},"closeness":"close|medium|far","note":"under 15 words: how c differs, or why rejected"}
Views must be one of: side, three-quarter, front, back, top, pair. For rejected sheets, keep only sheet, use and note. closeness says how alike the C photo looks to a1 overall.

Your output file: data\confirm\fashion\pass1_part2.json

Your sheets (52): f052 to f103, every number in between.

When finished, reply with only: how many sheets you used, how many you rejected, and the most common rejection reasons.
````

## 15. Select pairs: fashion part 3

시각 2026-11-04T00:46:20.039Z, 모델 fable, 에이전트 유형 general-purpose

````text
You are selecting product photos for a study, using only your own eyes on contact sheets. Do not call any API, install anything or run other analysis. You are only to read images and write one JSON file.

Project folder: <repo>
Sheets: data\confirm\fashion\sheets\<sheet>.jpg (use the absolute path). Each sheet has 5 rows. Row "A" is the anchor product. Rows "C1" to "C4" are other products of the same brand. Each photo has a small red index (0, 1, 2...) at its top-left. A blank cell means a photo failed to load; ignore it. Read several sheets per response to save turns.

For each sheet, choose these or reject the sheet:

- a1: an A photo.
- a2: another A photo of the same physical item, from a clearly different angle (not a near-duplicate or a mirror of a1).
- c_row and c: one photo from one C row, showing a truly different design. It must differ in shape or structure so that a careful person comparing two photos could tell them apart. Do NOT pick a C row that is the same design in another colour or material, the same mould or model, or a set containing the same item. The C product should otherwise look alike: same type of item and, if possible, a comparable colour and style. Prefer the closest C row that is truly different.
- c should be from a viewing angle like a2's, so the a1-a2 pair and the a1-c pair are equally easy to compare on angle.

Every chosen photo must: show the whole product (one item or a pair of the same item); have no person or body; not be a close-up, sole-only view, inside-only view, or packaging shot; have no dimension lines, size charts, added text, or props such as a magazine; show no brand name or logo you can read or make out, including on insoles, tongues, tabs, plates and badges. When a view is likely to show an insole or tag with text (top-down views especially), prefer another view. These are thumbnails, so also avoid photos where a small mark seems present even if you cannot read it.

Reject the sheet (use=false) if no valid set exists, and say why. Do not stretch the rules to keep a sheet.

Write the results to the file named below as a JSON array with one object per sheet, in sheet order:
{"sheet":"f105","use":true,"a1":0,"a2":3,"c_row":3,"c":0,"views":{"a1":"three-quarter","a2":"side","c":"side"},"closeness":"close|medium|far","note":"under 15 words: how c differs, or why rejected"}
Views must be one of: side, three-quarter, front, back, top, pair. For rejected sheets, keep only sheet, use and note. closeness says how alike the C photo looks to a1 overall.

Your output file: data\confirm\fashion\pass1_part3.json

Your sheets (52): f104 to f155, every number in between.

When finished, reply with only: how many sheets you used, how many you rejected, and the most common rejection reasons.
````

## 16. Select pairs: fashion part 4

시각 2026-11-04T00:46:27.038Z, 모델 fable, 에이전트 유형 general-purpose

````text
You are selecting product photos for a study, using only your own eyes on contact sheets. Do not call any API, install anything or run other analysis. You are only to read images and write one JSON file.

Project folder: <repo>
Sheets: data\confirm\fashion\sheets\<sheet>.jpg (use the absolute path). Each sheet has 5 rows. Row "A" is the anchor product. Rows "C1" to "C4" are other products of the same brand. Each photo has a small red index (0, 1, 2...) at its top-left. A blank cell means a photo failed to load; ignore it. Read several sheets per response to save turns.

For each sheet, choose these or reject the sheet:

- a1: an A photo.
- a2: another A photo of the same physical item, from a clearly different angle (not a near-duplicate or a mirror of a1).
- c_row and c: one photo from one C row, showing a truly different design. It must differ in shape or structure so that a careful person comparing two photos could tell them apart. Do NOT pick a C row that is the same design in another colour or material, the same mould or model, or a set containing the same item. The C product should otherwise look alike: same type of item and, if possible, a comparable colour and style. Prefer the closest C row that is truly different.
- c should be from a viewing angle like a2's, so the a1-a2 pair and the a1-c pair are equally easy to compare on angle.

Every chosen photo must: show the whole product (one item or a pair of the same item); have no person or body; not be a close-up, sole-only view, inside-only view, or packaging shot; have no dimension lines, size charts, added text, or props such as a magazine; show no brand name or logo you can read or make out, including on insoles, tongues, tabs, plates and badges. When a view is likely to show an insole or tag with text (top-down views especially), prefer another view. These are thumbnails, so also avoid photos where a small mark seems present even if you cannot read it.

Reject the sheet (use=false) if no valid set exists, and say why. Do not stretch the rules to keep a sheet.

Write the results to the file named below as a JSON array with one object per sheet, in sheet order:
{"sheet":"f157","use":true,"a1":0,"a2":3,"c_row":3,"c":0,"views":{"a1":"three-quarter","a2":"side","c":"side"},"closeness":"close|medium|far","note":"under 15 words: how c differs, or why rejected"}
Views must be one of: side, three-quarter, front, back, top, pair. For rejected sheets, keep only sheet, use and note. closeness says how alike the C photo looks to a1 overall.

Your output file: data\confirm\fashion\pass1_part4.json

Your sheets (51): f156 to f206, every number in between.

When finished, reply with only: how many sheets you used, how many you rejected, and the most common rejection reasons.
````

## 17. Select pairs: fashion part 5

시각 2026-11-04T00:46:34.040Z, 모델 fable, 에이전트 유형 general-purpose

````text
You are selecting product photos for a study, using only your own eyes on contact sheets. Do not call any API, install anything or run other analysis. You are only to read images and write one JSON file.

Project folder: <repo>
Sheets: data\confirm\fashion\sheets\<sheet>.jpg (use the absolute path). Each sheet has 5 rows. Row "A" is the anchor product. Rows "C1" to "C4" are other products of the same brand. Each photo has a small red index (0, 1, 2...) at its top-left. A blank cell means a photo failed to load; ignore it. Read several sheets per response to save turns.

For each sheet, choose these or reject the sheet:

- a1: an A photo.
- a2: another A photo of the same physical item, from a clearly different angle (not a near-duplicate or a mirror of a1).
- c_row and c: one photo from one C row, showing a truly different design. It must differ in shape or structure so that a careful person comparing two photos could tell them apart. Do NOT pick a C row that is the same design in another colour or material, the same mould or model, or a set containing the same item. The C product should otherwise look alike: same type of item and, if possible, a comparable colour and style. Prefer the closest C row that is truly different.
- c should be from a viewing angle like a2's, so the a1-a2 pair and the a1-c pair are equally easy to compare on angle.

Every chosen photo must: show the whole product (one item or a pair of the same item); have no person or body; not be a close-up, sole-only view, inside-only view, or packaging shot; have no dimension lines, size charts, added text, or props such as a magazine; show no brand name or logo you can read or make out, including on insoles, tongues, tabs, plates and badges. When a view is likely to show an insole or tag with text (top-down views especially), prefer another view. These are thumbnails, so also avoid photos where a small mark seems present even if you cannot read it.

Reject the sheet (use=false) if no valid set exists, and say why. Do not stretch the rules to keep a sheet.

Write the results to the file named below as a JSON array with one object per sheet, in sheet order:
{"sheet":"f208","use":true,"a1":0,"a2":3,"c_row":3,"c":0,"views":{"a1":"three-quarter","a2":"side","c":"side"},"closeness":"close|medium|far","note":"under 15 words: how c differs, or why rejected"}
Views must be one of: side, three-quarter, front, back, top, pair. For rejected sheets, keep only sheet, use and note. closeness says how alike the C photo looks to a1 overall.

Your output file: data\confirm\fashion\pass1_part5.json

Your sheets (51): f207 to f257, every number in between.

When finished, reply with only: how many sheets you used, how many you rejected, and the most common rejection reasons.
````

## 18. Select pairs: fashion part 6

시각 2026-11-04T00:46:40.987Z, 모델 fable, 에이전트 유형 general-purpose

````text
You are selecting product photos for a study, using only your own eyes on contact sheets. Do not call any API, install anything or run other analysis. You are only to read images and write one JSON file.

Project folder: <repo>
Sheets: data\confirm\fashion\sheets\<sheet>.jpg (use the absolute path). Each sheet has 5 rows. Row "A" is the anchor product. Rows "C1" to "C4" are other products of the same brand. Each photo has a small red index (0, 1, 2...) at its top-left. A blank cell means a photo failed to load; ignore it. Read several sheets per response to save turns.

For each sheet, choose these or reject the sheet:

- a1: an A photo.
- a2: another A photo of the same physical item, from a clearly different angle (not a near-duplicate or a mirror of a1).
- c_row and c: one photo from one C row, showing a truly different design. It must differ in shape or structure so that a careful person comparing two photos could tell them apart. Do NOT pick a C row that is the same design in another colour or material, the same mould or model, or a set containing the same item. The C product should otherwise look alike: same type of item and, if possible, a comparable colour and style. Prefer the closest C row that is truly different.
- c should be from a viewing angle like a2's, so the a1-a2 pair and the a1-c pair are equally easy to compare on angle.

Every chosen photo must: show the whole product (one item or a pair of the same item); have no person or body; not be a close-up, sole-only view, inside-only view, or packaging shot; have no dimension lines, size charts, added text, or props such as a magazine; show no brand name or logo you can read or make out, including on insoles, tongues, tabs, plates and badges. When a view is likely to show an insole or tag with text (top-down views especially), prefer another view. These are thumbnails, so also avoid photos where a small mark seems present even if you cannot read it.

Reject the sheet (use=false) if no valid set exists, and say why. Do not stretch the rules to keep a sheet.

Write the results to the file named below as a JSON array with one object per sheet, in sheet order:
{"sheet":"f259","use":true,"a1":0,"a2":3,"c_row":3,"c":0,"views":{"a1":"three-quarter","a2":"side","c":"side"},"closeness":"close|medium|far","note":"under 15 words: how c differs, or why rejected"}
Views must be one of: side, three-quarter, front, back, top, pair. For rejected sheets, keep only sheet, use and note. closeness says how alike the C photo looks to a1 overall.

Your output file: data\confirm\fashion\pass1_part6.json

Your sheets (51): f258 to f308, every number in between.

When finished, reply with only: how many sheets you used, how many you rejected, and the most common rejection reasons.
````

## 19. Select pairs: furniture part 1

시각 2026-11-04T00:46:49.611Z, 모델 fable, 에이전트 유형 general-purpose

````text
You are selecting product photos for a study, using only your own eyes on contact sheets. Do not call any API, install anything or run other analysis. You are only to read images and write one JSON file.

Project folder: <repo>
Sheets: data\confirm\furniture\sheets\<sheet>.jpg (use the absolute path). Each sheet has 5 rows of furniture or lighting. Row "A" is the anchor product. Rows "C1" to "C4" are other products of the same brand and product type. Each row shows three frames of a 360-degree spin of that product, with a small red index at the top-left: 0 is the 0-degree frame, 1 is the 45-degree frame, 2 is the 90-degree frame. A blank cell means a photo failed to load. Read several sheets per response to save turns.

The photos are fixed by the study design: a1 = A photo 0, a2 = A photo 1, and c = photo 1 of the C row you choose. Your job is to choose c_row, or reject the sheet.

Rules:

- A photo 0 must show the product from its front or a front three-quarter angle, not mainly its back or underside. A photo 1 must clearly show the same item.
- The chosen C row must be a truly different design from A. It must differ in shape or structure so that a careful person comparing two photos could tell them apart. Do NOT pick a C row that is the same design in another colour, fabric, upholstery, finish or size, the same frame or base with only the cushion or shade changed, or a set containing the same item. The C product should otherwise look alike: the same kind of item (for example a wall sconce with a wall sconce, a pendant with a pendant, an armchair with an armchair) and, if possible, a comparable colour and style. Prefer the closest C row that is truly different.
- C photo 1 must show a comparable side of its product as A photo 1 (for example both front three-quarter). If that C product's photo 1 shows its back while A photo 1 shows the front, choose another row.
- Each of the three chosen photos (A 0, A 1, C 1) must show the whole product and show no brand name, logo, label, tag or text you can read or make out, for example on lamp bases, switches, cushions or tags. These are thumbnails, so also avoid photos where a small mark seems present even if you cannot read it.

Reject the sheet (use=false) if no valid choice exists, and say why. Do not stretch the rules to keep a sheet.

Write the results to the file named below as a JSON array with one object per sheet, in sheet order:
{"sheet":"h001","use":true,"c_row":3,"closeness":"close|medium|far","note":"under 15 words: how c differs, or why rejected"}
For rejected sheets, keep only sheet, use and note. closeness says how alike C photo 1 looks to A photo 1 overall.

Your output file: data\confirm\furniture\pass1_part1.json

Your sheets (54): h000 to h053, every number in between.

When finished, reply with only: how many sheets you used, how many you rejected, and the most common rejection reasons.
````

## 20. Select pairs: furniture part 2

시각 2026-11-04T00:46:56.895Z, 모델 fable, 에이전트 유형 general-purpose

````text
You are selecting product photos for a study, using only your own eyes on contact sheets. Do not call any API, install anything or run other analysis. You are only to read images and write one JSON file.

Project folder: <repo>
Sheets: data\confirm\furniture\sheets\<sheet>.jpg (use the absolute path). Each sheet has 5 rows of furniture or lighting. Row "A" is the anchor product. Rows "C1" to "C4" are other products of the same brand and product type. Each row shows three frames of a 360-degree spin of that product, with a small red index at the top-left: 0 is the 0-degree frame, 1 is the 45-degree frame, 2 is the 90-degree frame. A blank cell means a photo failed to load. Read several sheets per response to save turns.

The photos are fixed by the study design: a1 = A photo 0, a2 = A photo 1, and c = photo 1 of the C row you choose. Your job is to choose c_row, or reject the sheet.

Rules:

- A photo 0 must show the product from its front or a front three-quarter angle, not mainly its back or underside. A photo 1 must clearly show the same item.
- The chosen C row must be a truly different design from A. It must differ in shape or structure so that a careful person comparing two photos could tell them apart. Do NOT pick a C row that is the same design in another colour, fabric, upholstery, finish or size, the same frame or base with only the cushion or shade changed, or a set containing the same item. The C product should otherwise look alike: the same kind of item (for example a wall sconce with a wall sconce, a pendant with a pendant, an armchair with an armchair) and, if possible, a comparable colour and style. Prefer the closest C row that is truly different.
- C photo 1 must show a comparable side of its product as A photo 1 (for example both front three-quarter). If that C product's photo 1 shows its back while A photo 1 shows the front, choose another row.
- Each of the three chosen photos (A 0, A 1, C 1) must show the whole product and show no brand name, logo, label, tag or text you can read or make out, for example on lamp bases, switches, cushions or tags. These are thumbnails, so also avoid photos where a small mark seems present even if you cannot read it.

Reject the sheet (use=false) if no valid choice exists, and say why. Do not stretch the rules to keep a sheet.

Write the results to the file named below as a JSON array with one object per sheet, in sheet order:
{"sheet":"h055","use":true,"c_row":3,"closeness":"close|medium|far","note":"under 15 words: how c differs, or why rejected"}
For rejected sheets, keep only sheet, use and note. closeness says how alike C photo 1 looks to A photo 1 overall.

Your output file: data\confirm\furniture\pass1_part2.json

Your sheets (53): h054 to h106, every number in between.

When finished, reply with only: how many sheets you used, how many you rejected, and the most common rejection reasons.
````

## 21. Select pairs: furniture part 3

시각 2026-11-04T00:47:04.031Z, 모델 fable, 에이전트 유형 general-purpose

````text
You are selecting product photos for a study, using only your own eyes on contact sheets. Do not call any API, install anything or run other analysis. You are only to read images and write one JSON file.

Project folder: <repo>
Sheets: data\confirm\furniture\sheets\<sheet>.jpg (use the absolute path). Each sheet has 5 rows of furniture or lighting. Row "A" is the anchor product. Rows "C1" to "C4" are other products of the same brand and product type. Each row shows three frames of a 360-degree spin of that product, with a small red index at the top-left: 0 is the 0-degree frame, 1 is the 45-degree frame, 2 is the 90-degree frame. A blank cell means a photo failed to load. Read several sheets per response to save turns.

The photos are fixed by the study design: a1 = A photo 0, a2 = A photo 1, and c = photo 1 of the C row you choose. Your job is to choose c_row, or reject the sheet.

Rules:

- A photo 0 must show the product from its front or a front three-quarter angle, not mainly its back or underside. A photo 1 must clearly show the same item.
- The chosen C row must be a truly different design from A. It must differ in shape or structure so that a careful person comparing two photos could tell them apart. Do NOT pick a C row that is the same design in another colour, fabric, upholstery, finish or size, the same frame or base with only the cushion or shade changed, or a set containing the same item. The C product should otherwise look alike: the same kind of item (for example a wall sconce with a wall sconce, a pendant with a pendant, an armchair with an armchair) and, if possible, a comparable colour and style. Prefer the closest C row that is truly different.
- C photo 1 must show a comparable side of its product as A photo 1 (for example both front three-quarter). If that C product's photo 1 shows its back while A photo 1 shows the front, choose another row.
- Each of the three chosen photos (A 0, A 1, C 1) must show the whole product and show no brand name, logo, label, tag or text you can read or make out, for example on lamp bases, switches, cushions or tags. These are thumbnails, so also avoid photos where a small mark seems present even if you cannot read it.

Reject the sheet (use=false) if no valid choice exists, and say why. Do not stretch the rules to keep a sheet.

Write the results to the file named below as a JSON array with one object per sheet, in sheet order:
{"sheet":"h108","use":true,"c_row":3,"closeness":"close|medium|far","note":"under 15 words: how c differs, or why rejected"}
For rejected sheets, keep only sheet, use and note. closeness says how alike C photo 1 looks to A photo 1 overall.

Your output file: data\confirm\furniture\pass1_part3.json

Your sheets (53): h107 to h159, every number in between.

When finished, reply with only: how many sheets you used, how many you rejected, and the most common rejection reasons.
````

## 22. Check furniture at 1000px part 1

시각 2026-11-04T00:53:02.241Z, 모델 fable, 에이전트 유형 general-purpose

````text
You are checking product photos for a study, using only your own eyes. Do not call any API, install anything or run other analysis. You are only to read images and write one JSON file.

Project folder: <repo>
Your list: data\confirm\furniture\check_part1.txt. Each line is one set: `<sheet> a1=<id> a2=<id> c=<id>`. Each photo is at data\pairs\photos\<id>.jpg (absolute path, 1000 pixels on the long side). The photos are frames of 360-degree spins of furniture or lighting: a1 is the anchor product at 0 degrees, a2 is the same product at 45 degrees, c is another product at 45 degrees. Read all three photos of several sets in each response to save turns. Look at each photo at this full size.

Keep a set (ok=true) only if all of these hold:

1. No mark on any of the three photos. A mark is any letter, word, number, monogram or logo on the product or on a tag or label, whether printed, stamped, embossed, moulded or sewn, however small, even if you cannot read it. Look closely at lamp bases, switches, cords, cushions, seat undersides, legs and tags. A printed fabric pattern with letters or script counts as a mark. Plain unmarked hardware, plain screws and plain stitching are not marks.
2. a1 and a2 show the same physical item: same design, same colour, same details.
3. c shows a truly different design from a1: shape or structure differs so that a careful person comparing the two photos could tell them apart. It is not the same design in another colour, fabric, upholstery, finish or size, and not the same frame or base with only the cushion, shade or an ornament changed.
4. c is the same kind of item as a1 (for example an armchair with an armchair, a wall sconce with a wall sconce, a coffee table with a coffee table), not merely the same broad category.
5. a1 shows the product from its front or a front three-quarter angle, not mainly its back or underside, and c shows a comparable side of its product as a2 does.
6. Each photo shows the whole product with no person, no added text or dimension lines, no props, and is not a close-up.

Apply the same standard to every set. Do not stretch the rules to keep a set, and do not reject a set for anything other than these six rules.

Write the results to data\confirm\furniture\pass2_part1.json as a JSON array with one object per line of your list, in list order:
{"sheet":"h001","ok":true,"failed":[],"marks":{"a1":"","a2":"","c":""},"note":"under 15 words"}
`failed` lists the rule numbers that failed. In `marks`, briefly say what you saw and where on that photo, or leave it empty. `note` says how c differs from a1 if ok, or why the set failed.

When finished, reply with only: how many sets you kept, how many you rejected, and how many rejections fell under each rule.
````

## 23. Check furniture at 1000px part 2

시각 2026-11-04T00:53:09.197Z, 모델 fable, 에이전트 유형 general-purpose

````text
You are checking product photos for a study, using only your own eyes. Do not call any API, install anything or run other analysis. You are only to read images and write one JSON file.

Project folder: <repo>
Your list: data\confirm\furniture\check_part2.txt. Each line is one set: `<sheet> a1=<id> a2=<id> c=<id>`. Each photo is at data\pairs\photos\<id>.jpg (absolute path, 1000 pixels on the long side). The photos are frames of 360-degree spins of furniture or lighting: a1 is the anchor product at 0 degrees, a2 is the same product at 45 degrees, c is another product at 45 degrees. Read all three photos of several sets in each response to save turns. Look at each photo at this full size.

Keep a set (ok=true) only if all of these hold:

1. No mark on any of the three photos. A mark is any letter, word, number, monogram or logo on the product or on a tag or label, whether printed, stamped, embossed, moulded or sewn, however small, even if you cannot read it. Look closely at lamp bases, switches, cords, cushions, seat undersides, legs and tags. A printed fabric pattern with letters or script counts as a mark. Plain unmarked hardware, plain screws and plain stitching are not marks.
2. a1 and a2 show the same physical item: same design, same colour, same details.
3. c shows a truly different design from a1: shape or structure differs so that a careful person comparing the two photos could tell them apart. It is not the same design in another colour, fabric, upholstery, finish or size, and not the same frame or base with only the cushion, shade or an ornament changed.
4. c is the same kind of item as a1 (for example an armchair with an armchair, a wall sconce with a wall sconce, a coffee table with a coffee table), not merely the same broad category.
5. a1 shows the product from its front or a front three-quarter angle, not mainly its back or underside, and c shows a comparable side of its product as a2 does.
6. Each photo shows the whole product with no person, no added text or dimension lines, no props, and is not a close-up.

Apply the same standard to every set. Do not stretch the rules to keep a set, and do not reject a set for anything other than these six rules.

Write the results to data\confirm\furniture\pass2_part2.json as a JSON array with one object per line of your list, in list order:
{"sheet":"h001","ok":true,"failed":[],"marks":{"a1":"","a2":"","c":""},"note":"under 15 words"}
`failed` lists the rule numbers that failed. In `marks`, briefly say what you saw and where on that photo, or leave it empty. `note` says how c differs from a1 if ok, or why the set failed.

When finished, reply with only: how many sets you kept, how many you rejected, and how many rejections fell under each rule.
````

## 24. Check furniture at 1000px part 3

시각 2026-11-04T00:53:16.076Z, 모델 fable, 에이전트 유형 general-purpose

````text
You are checking product photos for a study, using only your own eyes. Do not call any API, install anything or run other analysis. You are only to read images and write one JSON file.

Project folder: <repo>
Your list: data\confirm\furniture\check_part3.txt. Each line is one set: `<sheet> a1=<id> a2=<id> c=<id>`. Each photo is at data\pairs\photos\<id>.jpg (absolute path, 1000 pixels on the long side). The photos are frames of 360-degree spins of furniture or lighting: a1 is the anchor product at 0 degrees, a2 is the same product at 45 degrees, c is another product at 45 degrees. Read all three photos of several sets in each response to save turns. Look at each photo at this full size.

Keep a set (ok=true) only if all of these hold:

1. No mark on any of the three photos. A mark is any letter, word, number, monogram or logo on the product or on a tag or label, whether printed, stamped, embossed, moulded or sewn, however small, even if you cannot read it. Look closely at lamp bases, switches, cords, cushions, seat undersides, legs and tags. A printed fabric pattern with letters or script counts as a mark. Plain unmarked hardware, plain screws and plain stitching are not marks.
2. a1 and a2 show the same physical item: same design, same colour, same details.
3. c shows a truly different design from a1: shape or structure differs so that a careful person comparing the two photos could tell them apart. It is not the same design in another colour, fabric, upholstery, finish or size, and not the same frame or base with only the cushion, shade or an ornament changed.
4. c is the same kind of item as a1 (for example an armchair with an armchair, a wall sconce with a wall sconce, a coffee table with a coffee table), not merely the same broad category.
5. a1 shows the product from its front or a front three-quarter angle, not mainly its back or underside, and c shows a comparable side of its product as a2 does.
6. Each photo shows the whole product with no person, no added text or dimension lines, no props, and is not a close-up.

Apply the same standard to every set. Do not stretch the rules to keep a set, and do not reject a set for anything other than these six rules.

Write the results to data\confirm\furniture\pass2_part3.json as a JSON array with one object per line of your list, in list order:
{"sheet":"h001","ok":true,"failed":[],"marks":{"a1":"","a2":"","c":""},"note":"under 15 words"}
`failed` lists the rule numbers that failed. In `marks`, briefly say what you saw and where on that photo, or leave it empty. `note` says how c differs from a1 if ok, or why the set failed.

When finished, reply with only: how many sets you kept, how many you rejected, and how many rejections fell under each rule.
````

## 25. Check fashion at 1000px part 1

시각 2026-11-04T00:55:24.402Z, 모델 fable, 에이전트 유형 general-purpose

````text
You are checking product photos for a study, using only your own eyes. Do not call any API, install anything or run other analysis. You are only to read images and write one JSON file.

Project folder: <repo>
Your list: data\confirm\fashion\check_part1.txt. Each line is one set: `<sheet> a1=<id> a2=<id> c=<id>`. Each photo is at data\pairs\photos\<id>.jpg (absolute path, 1000 pixels on the long side). Read all three photos of several sets in each response to save turns. Look at each photo at this full size.

Keep a set (ok=true) only if all of these hold:

1. No mark on any of the three photos. A mark is any letter, word, number, monogram or logo on the product or on a tag, whether printed, stamped, embossed, moulded or sewn, however small, even if you cannot read it. Look closely at insoles, footbeds, tongues, heels, soles, straps, side tabs, buckles, plates, zip pulls and hang tags. Plain unmarked hardware, plain rivets and plain stitching are not marks.
2. a1 and a2 show the same physical item: same design, same colour, same details.
3. c shows a truly different design from a1: shape or structure differs so that a careful person comparing the two photos could tell them apart. It is not the same design in another colour or material, and not the same mould or base with only an ornament changed.
4. Each photo shows the whole product with no person, no added text or dimension lines, no props, and is not a close-up.

Apply the same standard to every set. Do not stretch the rules to keep a set, and do not reject a set for anything other than these four rules.

Write the results to data\confirm\fashion\pass2_part1.json as a JSON array with one object per line of your list, in list order:
{"sheet":"f000","ok":true,"failed":[],"marks":{"a1":"","a2":"","c":""},"note":"under 15 words"}
`failed` lists the rule numbers that failed. In `marks`, briefly say what you saw and where on that photo, or leave it empty. `note` says how c differs from a1 if ok, or why the set failed.

When finished, reply with only: how many sets you kept, how many you rejected, and how many rejections fell under each rule.
````

## 26. Check fashion at 1000px part 2

시각 2026-11-04T00:55:30.054Z, 모델 fable, 에이전트 유형 general-purpose

````text
You are checking product photos for a study, using only your own eyes. Do not call any API, install anything or run other analysis. You are only to read images and write one JSON file.

Project folder: <repo>
Your list: data\confirm\fashion\check_part2.txt. Each line is one set: `<sheet> a1=<id> a2=<id> c=<id>`. Each photo is at data\pairs\photos\<id>.jpg (absolute path, 1000 pixels on the long side). Read all three photos of several sets in each response to save turns. Look at each photo at this full size.

Keep a set (ok=true) only if all of these hold:

1. No mark on any of the three photos. A mark is any letter, word, number, monogram or logo on the product or on a tag, whether printed, stamped, embossed, moulded or sewn, however small, even if you cannot read it. Look closely at insoles, footbeds, tongues, heels, soles, straps, side tabs, buckles, plates, zip pulls and hang tags. Plain unmarked hardware, plain rivets and plain stitching are not marks.
2. a1 and a2 show the same physical item: same design, same colour, same details.
3. c shows a truly different design from a1: shape or structure differs so that a careful person comparing the two photos could tell them apart. It is not the same design in another colour or material, and not the same mould or base with only an ornament changed.
4. Each photo shows the whole product with no person, no added text or dimension lines, no props, and is not a close-up.

Apply the same standard to every set. Do not stretch the rules to keep a set, and do not reject a set for anything other than these four rules.

Write the results to data\confirm\fashion\pass2_part2.json as a JSON array with one object per line of your list, in list order:
{"sheet":"f000","ok":true,"failed":[],"marks":{"a1":"","a2":"","c":""},"note":"under 15 words"}
`failed` lists the rule numbers that failed. In `marks`, briefly say what you saw and where on that photo, or leave it empty. `note` says how c differs from a1 if ok, or why the set failed.

When finished, reply with only: how many sets you kept, how many you rejected, and how many rejections fell under each rule.
````

## 27. Check fashion at 1000px part 3

시각 2026-11-04T00:55:35.682Z, 모델 fable, 에이전트 유형 general-purpose

````text
You are checking product photos for a study, using only your own eyes. Do not call any API, install anything or run other analysis. You are only to read images and write one JSON file.

Project folder: <repo>
Your list: data\confirm\fashion\check_part3.txt. Each line is one set: `<sheet> a1=<id> a2=<id> c=<id>`. Each photo is at data\pairs\photos\<id>.jpg (absolute path, 1000 pixels on the long side). Read all three photos of several sets in each response to save turns. Look at each photo at this full size.

Keep a set (ok=true) only if all of these hold:

1. No mark on any of the three photos. A mark is any letter, word, number, monogram or logo on the product or on a tag, whether printed, stamped, embossed, moulded or sewn, however small, even if you cannot read it. Look closely at insoles, footbeds, tongues, heels, soles, straps, side tabs, buckles, plates, zip pulls and hang tags. Plain unmarked hardware, plain rivets and plain stitching are not marks.
2. a1 and a2 show the same physical item: same design, same colour, same details.
3. c shows a truly different design from a1: shape or structure differs so that a careful person comparing the two photos could tell them apart. It is not the same design in another colour or material, and not the same mould or base with only an ornament changed.
4. Each photo shows the whole product with no person, no added text or dimension lines, no props, and is not a close-up.

Apply the same standard to every set. Do not stretch the rules to keep a set, and do not reject a set for anything other than these four rules.

Write the results to data\confirm\fashion\pass2_part3.json as a JSON array with one object per line of your list, in list order:
{"sheet":"f000","ok":true,"failed":[],"marks":{"a1":"","a2":"","c":""},"note":"under 15 words"}
`failed` lists the rule numbers that failed. In `marks`, briefly say what you saw and where on that photo, or leave it empty. `note` says how c differs from a1 if ok, or why the set failed.

When finished, reply with only: how many sets you kept, how many you rejected, and how many rejections fell under each rule.
````
