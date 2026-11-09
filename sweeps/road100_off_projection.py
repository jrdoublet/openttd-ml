"""Exact ROAD100 opt-in source hunks projected away for frozen legacy audits.

The fixture was built from the original working tree versus the strictly
default-OFF ROAD100 experiments. Each replacement requires an exact, unique
current hunk; partial or silently modified experiments fail closed. Historical
SHA fixtures remain untouched. This is a source-level projection, not a claim
about runtime equivalence (verified by real paired smoke benches separately).

To recreate a fixture during initial review only:
    python -X utf8 sweeps/road100_off_projection.py --generate
Never regenerate a fixture to make a failing legacy hash pass; inspect source.
"""
from __future__ import annotations

import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = Path(__file__).with_name("fixtures") / "road100_optin_hunks.json"
SITE_FIRST_FIXTURE = Path(__file__).with_name("fixtures") / "road100_site_first_hunks.json"
V30A_FIXTURE = Path(__file__).with_name("fixtures") / "road100_v30a_optin_hunks.json"
V31_FIXTURE = Path(__file__).with_name("fixtures") / "road100_v31_optin_hunks.json"
V31B_FIXTURE = Path(__file__).with_name("fixtures") / "road100_v31b_optin_hunks.json"
V32_FIXTURE = Path(__file__).with_name("fixtures") / "road100_v32_optin_hunks.json"
V33_FIXTURE = Path(__file__).with_name("fixtures") / "road100_v33_optin_hunks.json"
V34_FIXTURE = Path(__file__).with_name("fixtures") / "road100_v34_optin_hunks.json"
V35_FIXTURE = Path(__file__).with_name("fixtures") / "road100_v35_optin_hunks.json"
V36_FIXTURE = Path(__file__).with_name("fixtures") / "road100_v36_optin_hunks.json"
FILES = (
    "builder_road.nut", "candidates.nut", "economy.nut", "globals_pre.nut",
    "info.nut", "opcode_exact.nut", "settings.nut", "task_projects.nut",
    "task_road.nut", "po01c_regen.nut", "po01c_generators.nut", "persist.nut",
)


# ROAD1Y-B2 was recorded on origin/master with seven unrelated RAIL-SIBLING /
# RAIL-OPEN additions embedded inside its very large contextual hunks.  Those
# additions are not ROAD1Y code and MUST survive projection of the merged
# master+RAIL bundle.  Keep the historical fixture and its normal projection
# entirely unchanged; the reviewed merge is the sole exception, identified by
# its exact input AND B2-projected SHA256.  Unknown revisions fail closed via
# the historical exact-hunk matcher rather than silently losing rail features.
# Each tuple is (merged SHA, B2-projected SHA, indices of RAIL-only hunks).
ROAD1Y_B2_RAIL_MERGE = {
    "candidates.nut": (
        "7b665f4b9035b8955212683573bfd0b340eaea2dd4a69d8563f1ece12747857d",
        "a94a6b536e8fa44b4af2255925febd9738016d522003753068d3702321e7d4a1",
        (7, 8, 9, 10),
    ),
    "globals_pre.nut": (
        "7ae9ad7cde04ceb382314f9d1ccab05125c52fab4cb22defd177dbfd35023fd6",
        "a9d97aa05e649cedc1234d633e2f3e38cbf950bb9b84196b5e82b4c65b7707dc",
        (1,),
    ),
    "info.nut": (
        "6332a1c7f17f8b7054b4a0846149c57b8ecae4cd8b145c62b92ad255a4bdf27a",
        "1c99cd605191af473382027cb70ccf8060e6e01053bfa8fc6a8b753f3d4c0bb1",
        (0,),
    ),
    "settings.nut": (
        "d335e8528c69b778059bfb0ce016159bdbbc2caaa080f514de45ff49333d8177",
        "4dffcc7d7d0f3800dc06a55da74e703fa4c572c6683ee6ad5fa0ecd12ab93640",
        (2,),
    ),
}

# Selected callers remove newer RAIL policies *before* calling ROAD100 (notably
# n75_mc_legacy.historical_bytes).  Those intermediate sources are distinct
# from the live merged file, but remain fixed and reviewed.  The pairs below
# pin their exact SHA256 before and after subtracting ROAD1Y-B2.  The stages
# are RAIL-LONG OFF, RAIL-SEARCH-PRIO OFF, then RAIL-DEPOT-SIGNAL OFF, in that
# order.  Identical stages (no edit for that file) need only one pair.
ROAD1Y_B2_RAIL_MERGE_STAGES = {
    "candidates.nut": (
        ("e58fcedbb7ac99897236aeecf30045a5d4443ec21d8ac00d4508565582ffe0ee",
         "82253f50c21aa1545f65997a5c1aaf880cc99737ebca4f38dcf9029490f456bd"),
        # The fully stripped candidate source is BYTE-IDENTICAL to
        # origin/master.  Do not whitelist it: source alone cannot distinguish
        # that legacy input from a merged intermediate, so preserve the
        # historical projection for this SHA.
    ),
    "globals_pre.nut": (
        ("d0548c85cd11d62de13e4eb1566088d77a15ab6490b3a30a01fb27eda3110424",
         "a5fac92a00c72cdcb7fb091bab51ef14092f76fd92debe759c02986970ee0e1d"),
        ("95287db807334e84c5a1146a7d2ca446d6c464aa9daf6cd2b55cd7d76d19ad3d",
         "8ff485029940bed662ea10a539e1c47a94b0decda19de2c3954020b09a1dbca7"),
        ("c6861e400454c652fcf150e9148be6d96d6bf7c370df15009bfedf9732bd90e9",
         "09844bbed074c149fca50293bc9bf9e75f19f3ada9cb0f533a585f6bcf9a6b57"),
        ("42d7708dc890be6adbf5936c4879075ece39a030a777318edcaaa77b719a86d0",
         "fe3ffab63749bc618f3ad46c73ed5bbf193727e94ef5c52a1ff13d5a6e5838cf"),
        ("bbcda5db139fe06a1e9440c003c96203260c957a94b9ab1038609ff9f2e7f732",
         "18321f3b50751331160fe8d40a4f44c869a5d423f04f0a1d3e2ab3fe2e277cda"),
        ("8259ace0676901f7203b1a38207f94d62ad9b0cf948abe3b6a321e05d31e4daa",
         "726382e286bcba6cdae6e19b34225f5a5e6b5814d73e898d6a87a7f918bf9908"),
        ("1deda3150a9e324b738758aaf7a25f1d1c8c3933f363652a22f992b9146218d1",
         "11c544053875e3cba179310e39157a3ca4f3a6b0746102afcc790966b15e6c9f"),
        ("06d784ef3eb2826b7ede17b488f46bb92ddcab9e433fed3af68077a2de1d9d4f",
         "421d81c528a9a32bc8b010fedb73f7373d5b2177a910b49aa4f057c714d48429"),
        ("b8179aa8881e140d59ccfb39eb5513a181aab4f3d73dbc4343b014334dafd96a",
         "ea7fe4282005958f431ee346576fb0fb6e9531bd688a4fba5a4e501c8fc64d17"),
        ("5f8139b23a1d93ebeb39ecf0ccc1a8cf10baf5d7586f000164f3b246efc7b170",
         "d9cb6b939ae1006f60b9ef06c7d7f1466d48d676b59f1a129afc19aa52441338"),
        ("152c958201a5b07e6a78a80bad9fff3659ec926a5463608a3b2754c9444936ab",
         "8cde7b95d3352a1e9f190660b71fdde66e1b61b783181f897fb8490cb3036c93"),
        ("e57e4bff913825c44ae107f6b02ad31e85004bee58e9e2a834f5e2b530e850b7",
         "01608e1b235e497d8c8c43fcc74b76ba5dcf6fc63fd1efc22891a0aaa76ffdc3"),
        ("01dc09c39b8c5ad65744e83c71406d84b80b2b3fe9a1395ff9a5a20d4855f4ad",
         "f4aa24a64c36cd4179af0c5a58e61f7eae554b04f43a843d9681cb02b6d377db"),
        ("948b150eb750862dde558c08164bd1d03d32080b8bb4ad32fd3a8a82b224180e",
         "37bee2c9077de875f6f6de52bdd9451a0ba9ca446cb47eb2ff2514578360310b"),
        ("9a4c89e8b949a2c57c5ff18167b14183bb8b445015c52aea5ea494286f0de516",
         "c2055ffc73f83864876c7272f27fee7e84118042de8a0ecfb9fc506fc015d2cf"),
        ("25dc9a251d1a390f8efb825a00473d22c169e5771a4f5cac8c9fee13f8c8826a",
         "eb92671eb828e834459cab33943317e65f428e2d2083dc4df50a1a32fe958b3d"),
        ("6146dafd7b9d5714da012cfc419d8049e39b46e74264c72af98850aca2c5fe1f",
         "ddb53473776ed4961c13d01a7009f7fef6700b8fdcd9e4fbac2b8db4d4fe9070"),
        ("20b2b9ff058607428cfcbd182d1ddb6fb504509c31fcb540ecd3954153b8626e",
         "066953565cceff54642773f80333e56baa7c91406d92a984e1c25c28bea76d8c"),
        ("259de008403b3ef959293efca5ea068dcc7b37731d68af3a0925aa4b68f947b1",
         "4fcce7d7df545aa6cdc2a426a8c09f655567447cf421bc33272f2c3aae1ffd03"),
        ("be832257ac7eed33b6f273015a67dd014767c141c9422dd55d0ffc70813aff8b",
         "3efb8e2a3eff014892dd7969b5d33a3036dc27207616de0f9a1f5b99c2cbe27d"),
        ("91ed7c2164d4640f6b951a7c36411dc2ca22449ef7accb9ab08e50bb027a6ed9",
         "1ab418fbfc2f5b434ce39c33da468dfe1c957b1f5e2209f94f3153f1b53b3adc"),
        ("d24cc986089d1821359fa59c433d6b5117bfce0e1df9f00d639f8a3669820a88",
         "71769a8fcf89996001a958161942e8a31785a46c94021c8528bf43477321dc2d"),
        ("3105e4d1c0bf9fafc91ac0dde3374aeb3ab89881723e90ee50d2916773b92c14",
         "34944ed2f7d95b3488c0a7ac7a9398eafdf6a44c4eb6d6e592771d25aa10563e"),
        ("5a09ece6dedb2cfe93bab5b2af9952d13ab9e5b23eca78bc3a700ea0bf3612d4",
         "17eca119c607b302897225f53ea1d0ed60f01aec62bc546ed5c580507a94c497"),
        ("f4890b45ce169959cab5cf70e7766ca2ac6bfd3ed125d9e7114732fdd55f1fb2",
         "6acbd19983114247e4591dead2fb9f925a343ebdbef140d2d4c69e05602c130d"),
        ("2d62d3214e94cd1ef86fbe6a7dde14d7ab95dc9ed4f0385a594a6c433f6f90ac",
         "bf5896e95531ef05995306a8c10a9015e5692245b92f7e546c75b09c7fd52903"),
        ("f55e0027fefada29468b47d2378bb791d1c55e54b1dd84467230cde8fdf4abd4",
         "2c6818cd40b41f21db6d1021db5a05dabea8a0601a5058bf9fd5d4a3409f3d22"),
        ("4c0cab11afb3086bc1dfb5095eb213ba8a92fcbdf5ce19b66ae2f1f763197e30",
         "51029be2e36599c78edd92647fd2100ded2ecbd239e3306a823d74b6719b2a94"),
        ("d87f593bab8e42a8d27381a13fe9fe49538d3c8a347197ff582e63d03b690495",
         "049e44803cb59c7f6678a8d111ec4ec4b9527264c9cc018a4a5861739aeba187"),
        ("e124e7b3a5ed6c44d3b8b253012ae83080276ce5664fd759a138391feb195de7",
         "670afc78cd13882abd21cd18cf26a8a6a01ce15e7c3401925322aeed5d9033e6"),
        ("4ef40b70464834320c3067e2fb69d922e78074584e3a334730bcc8ecc60a2958",
         "8f11ed229d7c8f2db9d2e497f73d8012127557828b3e85ede6ba8b12e903656d"),
        ("12707e96e3c03b1ee895cd73fc10cf7dfffc39c8ddfb86930b5b75a5c8603e11",
         "8db2c15d09110cf06c4be3ca583695f7f5a9f1bbddc337f8f01e42acc852faea"),
        ("d70577622aa7949b3655e515929efb60dc512e96fbc21258708eb18455a9f2e2",
         "d7fe4ab36dc60039b4cebd56b327ccd4c3199371aed92ba73bb5b9b898e84a0d"),
        ("33443705bcf7b9051a2a3ed918fee6cd08fa7ba187ad4332323155bfaeb0e8fd",
         "ee7996196e0669c92150403721d43efefef7584f8744135b41698d75f50f3424"),
        ("464d5140f46d38235dc313c8699dea7116aace2665326cb3bbae2ffd182b6b79",
         "684257ca4bcb463389b0b9e2084cf3f226afcdca47aacc7223649d2423fabd29"),
    ),
    "info.nut": (
        ("0e6e6e30aaae1b814dc8afbaad515347e2dc05aea133cd12983a7abc1fce26f1",
         "db4e98d70522a49ae3242441b5479e22ae3422bc0eca772677da37f8aa04f0d2"),
        ("1fbdac0c3e35ee9812033b7456620b512f7b641cf780ab1c74ff0f1dcc0e3e63",
         "46b702bbe37532bc8212af5058147caa5b12cce41ac427f3a3b58d244907d19f"),
        ("86d67cac63199b4a1ab267acb533513b1f2ab5391558988351eba0e7efc261aa",
         "8bf5ca75fe04815effbfa632386adc2118bd78b2147e951a8a067505eb817bdc"),
        ("ebb95bf341a59e795c542dc3502d7105f2f9f3413daabd753467230d4dc97ffc",
         "65c458f5290ceb7c0d36e706bf25a9ac796e6cb833ad534242786868fafd6057"),
        ("978be3150bee4ff41f31b2cea1cfcc106e8e3bc82ce048ab42d434111a06338a",
         "aa97ac5cffd849ab30b7bcf9c60bff018c488d201288c77ec88d0708a0666dd9"),
        ("d748080325db7968857449ced8d716621519f80ef70b6f4719ff5eff2ea439b5",
         "e2138b136cc1f72010866dc95a1cc41d9fd202653505380d0d53d77a45ff33ee"),
        ("58f6702b0eff983cc6773101dd545de91c1ee992a0ad58288ca40e43e41741f8",
         "d8f95765dd460bac123773ee05c1c6bc2c401743747aff6eb0da098a9062a113"),
        ("3e2fda7483d4cd0bc4d0937d3a5dc8e2450640c0e7935b74bcf184ac10992dc9",
         "1b7361f6ac7bccb65c9222eb9e8aa5ade1b7b5b967e46acb80d0539ccfd8d462"),
        ("3e3328ceaa0cbe79e2d5d9d233911e653a03334f3f92de8935494c15c5de074c",
         "28ac6c304b6f9b3f66229fa43bf94f53507bf6c50e30d1ea05b8e989c0dd5713"),
        ("c4b78830d3ba028b4bcdb9aa9e7c8dd81d40e0683dddcb99c8d0c6cbf5f15d73",
         "a76c97d53fd92bdf86ce4856cc03e6115050fb7a06e21d087b9698e7d869f717"),
        ("622044cdd917b97ed105fa7a602cc67f6d8f1fc57743f5005d49ddad0c401f11",
         "106e4e7ad1485a21f75d14148a64386d22c7771db40923f871e34954e38d7bd4"),
        ("52e08e4254a6b7facc2e379b217b3e307dfc980e7d3ed8472fb1250bb550ecbe",
         "2bdd3cbfd1c9b74f4c8ffe8f01ed98624a8e306195413522799dca11e898d6b7"),
        ("5afe4ba29734887b9e62e82d9eb651ae8d262e4bfe0d422d9e866a8f0d765334",
         "6f3ec1b7219161d19ef2a877eb03d30dc15149a075ebe2c724de793cc0c6bbaa"),
        ("52960252390bdb1459f7c5294c2eaba7ee0f109856f25ef9910e403e5d1815cc",
         "726c1d18411e44716fb8ad1331bcc600de3998dfb563ef933088aa1ca9bddfe1"),
        ("209bef23b656652fea965f462b529e4660f444c2081a46081971f602b8f7dedb",
         "7f7ad61738e10db417662740060bd49a470bad2c7e73a6645138265b8cb50281"),
        ("c4c5f4c178c39eb7b5c8fe2b43292284b007ac446849613fd5118784d0fd938a",
         "b981d4146d202ed81e2406d61122ff024d1dcd1e5e419999a4c93470c4c6c285"),
        ("7fe60580b67641875888559bdadaa269f1ef3d2c9645d4f0f2acab1a73216e98",
         "effef39f49a8bd776b0ba36a74dc9c64abb1788f9bb0d044cd15fcf6ac007fbd"),
        ("83bef1e25353007b9c4f82d61213d280d39f4fa5d4f563efe3ee85c7486c3e4a",
         "65f5b21e4d465d0717693cf1e752b0dc85bbc7c1d4e3858f6512f3d029959a73"),
        ("9c830d318beccc9ab8eca51d10e19de67dfab33e52d229e6c29bd6d40fe814e0",
         "4e428e6aee082d429926f2bc5ebcc5d375bb9a3bc6b35308b6e13351a6f499f6"),
        ("fd13a73f8a541192d97eaee0fcda9e314e8a02f0aa18d4b66f12c664b24a19e4",
         "f88638d96044336c3ac4c69f4e311c7e187dbb7f20799dfd56ed7ed071ca3a47"),
        ("2fee2e33c0e4430174156c6feed9514f0a9b65efb8a5767df4724202a36d094e",
         "937ff51f9df871897d57897f5d24f9e5ce92e1c17222a77329da1f043f2ee71c"),
        ("c24c7ab5e145888c93aa906d465953fcacf9fba6525b791289a412ac532f8e5e",
         "3a67ea1d1f5062b711076d5617132d2de21bbde88f2f39d10e5a5a618e68bdb3"),
        ("dee66bf13ec6aadaba2aea8a4f5173be48f53f3e201b7ad7dd234ffbe5c042e3",
         "70a733f9315fd0473f6bcd1e2565fa2603e575b87f1bb894931c3307e179d748"),
        ("ea8db6b3453ef780849a89abfb09d1182b7d6485096c71ee8391f73fc8b70822",
         "6721ec5a23e724be334abdd0e4c41cd21ca03522cc4815f4ebb42bee3e90aa0a"),
        ("08aeced5746be1bd3b1bcf0bba3b100527517f36ae8b6847a986d233fa055941",
         "62fdbc59adc8739258b8eb2c75b5999219ebeb791b21ab2d00eb82def38bc5bb"),
        ("0b74c4e31d6e305baeb94305d33fb9ef754afa623fcf1fa571ac8a25af4ede08",
         "0814d0b118b0f2bd4b64906be2692e9a994a83733c0c6b6654143d4ef2928350"),
        ("4ab730803439b69493f1f5e2565480a9373ae08ceb18f02a0aeb73ae509578ef",
         "1b7dc39e77c50c82e20c3138cc5d3664b6526a578a9c53e28ca26c59ef324208"),
        ("b59a03ab0a20b72c431ac2fb3f55a3e75f541f7d5e5d01946f34f519b0509cff",
         "506e90a1aef1305b5f06d49e50bccdd13b22f36a70ae342daf9aeaaf72cb2928"),
        ("9b242508f406296f9d46d8d5f3aa079015696bcaa63ab7f74eee54814849e62e",
         "613fa8a851b25f55d8f4694482e02babe657d5149937db0e0ea0d798635a65eb"),
        ("eaee50ad635b4baa4f153b2f065d5ff535fbbb9e4907388acab2e740fc855037",
         "a4e8364319ceae0df255388533f7fa2766188e7fb4b7d4669c9a658a4eb2587a"),
        ("c50b324709e661026e9ca3f54467514a85dc1958fb7fddeff202db882a94c130",
         "5396ff298f0137b9f40748821b4623f2046c6b9126206c714d1ee9fb4d38fff5"),
        ("67452181d5c768051dbd0690ebdc31be581a078b293d62e7a67fd68767378ea2",
         "af6a9727e6c769cb098d4c62073a255a371d19bbbcf9844c1e946933b70cf948"),
        ("746d6afe204f2e91047dda8915de51055bb21b101fe42435abefe4a3156cd596",
         "c432de662bb07ee165f20d98d90952ffcb2df04abe74ba1d804e7a5f693af7d6"),
        ("30f28f3faf699b1944565246bc5f9d3df4ad31b23652c8b1787f076fe0542705",
         "eda99ade4949433c65138666aa2a6687894ebca893427780abe4e2b4de3d5143"),
        ("c21bd72215089413b104afcf26e619021ada40f841a979a7743102e16c8125ae",
         "f59820a88405a0ef4b577fd9227e5dfd53aae9358bbbe361d9a3bc2cb4ae063c"),
    ),
    "settings.nut": (
        ("32542fef11a2bad6fbc7716a4e07a52758e7a2e358af172d2b43c3ee4a0a59fc",
         "e9a77ce85ffb1a8b552c2022b3aa1f6abf53797c9813a09b62118d9840de1ec4"),
        ("4ba30a2a9a44059be4f33da8906bf7c289be24cb49376563616ce487a111f483",
         "5739b3a18c226c969200f142dfa5e173002dec76ff094090b3c120f2fc597bb2"),
        ("12ff68193bd638c2f4eb5139151fe872bb05fb163bda1a299610e3481ae1e2e3",
         "5a9c5cddcd059ba8b8679f949d19d75d8c5213427d60375a9421a17dbe362567"),
        ("1dadbfebb825771eec820582830227c6b2d29580c2eed6f392517f731d5eb02f",
         "4ac2ffaed7f5a5c7236591422a5154162570d649c48ff36d8db34384dcd20ff9"),
        ("691263ee1f004aee0a65af986424c19878a43932197f3042972ec809d1755f17",
         "f37e4ec74c036fbd548da3c31e9f896f70cc6f860ee0254471da47fd2a2e2df0"),
        ("1ebe32ba82706e84e7d7a87e3771b4d565cd11d4384d2c5a3995a749a5e06ecc",
         "7b34f37fbfb4af1a7e64c43efcea8d1d2c89de0cfc375c3e029befa204853e1a"),
        ("e6b49db8010b756a5216d9762bfc62f8c9cc3d93ba47ee2801edbaa0a0079abb",
         "762b4d234b7b78925bbce0416536cf46d9bf3195eca6a96e82ca31a0c979ea49"),
        ("a612a9d620386480bf471d2e91357b8b9f6a02a301009c96759208691719b313",
         "57ada069b47ca127fdbae85acfdb692e3830f887ce859bafc50136381c8db343"),
        ("d7f22c72bf3791c1f5847979078cd9a4b0d6744ffdda9bbebd4d6717d5a09621",
         "8113227fff612356ac02da2ca3d15aed00512fb5d3487f3ef2eedc5fac2fc038"),
        ("37bf5061d7aa8318a9ddc6deb078e5a106df34523ab1e5430eadb2c2b94fb7ad",
         "c60cce71d9449c9fa82ff7603ad35a4771c8b268f1f909b2a98acc2a33ea9341"),
        ("3e57ab494ece16f9251cb227343b0bd625fe2c5e711a48a3c78263a3164fb18d",
         "15c807ec4b5daa1cbc2632af5409d454f781992761028cfa76467672e5b8945a"),
        ("b72474a01e76f80d720b253c94c1a3975012c9fe437e156a52e86d39291ca985",
         "cf12d6aedffb428b03fc82d067741eac136ac44527ae4e6f6513710c2223623f"),
        ("1656a16eec6e2605b8037627bf3a9bcce102d4dd3624373100566db4dc3ca8ef",
         "bf44a0d78690274c5d27aa878df4d1ecb268d6cf97f117132dca305392151e95"),
        ("2de80a8d590ce383514d06481a5c1aa2c127d78e5c1e6ac08093cc603c55cc58",
         "7e6be4d6ca614019df513443627d0b803c909aeebb08f300198eaae3358a04ea"),
        ("6d8cbdd5c3ea9450c7f3fc49947ad37cf6d73f3f8033cc14dd2435b308a977c6",
         "80a2728661f8efd42d99085509f3cba481f8a5b47a5f5d241512e3615fd8520d"),
        ("0128615652727a55c131b5460f0d7e4aa9a4432288c6307cc9151f39e2c82766",
         "0cbd92e63be7745ad2d214ff8a405eaa365e4cfaca55802cd6df02f317336649"),
        ("4b7711341b636ec5abd1fb65a70919076a428f378cb8c05f6a5253994f18a92b",
         "987924f1abfcf77480ffd35062d28244c0b5d4d5cb197cb9aa7c1c859c64ec95"),
        ("bc87f445999820d29e0f8254964d2d6981be219bbb6fb75b6823c2320aa3a07f",
         "b32453e249b6de04a94814fb4d44810bddee8063ca5988631017335db6419b45"),
        ("497a9ab5240acbacc7125eef318d790e7814504f720c58d6c9bfc0a1f8afebd4",
         "fe844d1964dfd67dd349484cc32ccef5958e7e2e5cb4308ed91ed8efe7b02f57"),
        ("a97a8451a2d5376f9c9812372b76dfd60c5e3f7c5e139304ce157f159e22abff",
         "73f8562a5a3680e8488d2fc94e44deb900e40c22fba118d6c12e0c5f9691b08e"),
        ("6fe6a70125107e2bf409f1aa292032149fe4ed9c4436bbacde75395edb803644",
         "f927ee05fb06b367734df321f00cb8ad85f81c61785ca259ada109a20e951c09"),
        ("e11c9d207adb56c936dc19a26b3bb1f3884b033cc1d949214be98bc302c3176c",
         "7ae04f89f23401e4a5977990c934a3aaeae10d2d61a967d69023a98da2b9dbc1"),
        ("50ccb9a443a7c09ed1d94e11519e4c6ad67b19c89eafcbf798b7cb8f0fadbd59",
         "bb24bf07999f81a88190b692bd97b82ad13bba714b9736d878be674d9f135147"),
        ("fd02c8a929f1345fb4ad6f958d939506b2cd2018ec4e270228f46758389542d4",
         "f90ba4ca14d4cbed0f690e8949b63359ea302f1872d3451cf85fcf8d91042e88"),
        ("9fdc13d9110022e2421f61745bb2b811308dcc34ad1152390e828a8e8abc6e77",
         "e49d8ea9aca0381c7b6cde28b62a4520855a843eaeb8ade9ceb2efe137de58c1"),
        ("e0fb2de5b2f976c01a7e225e40013c346c3f2a0d1c7e193c6db90c4db10be871",
         "b71a757c7414140425bf633a468a03941db856da7a152be7fd76f9244b71b384"),
        ("9f345572aaf13ca7f15a22cbdc2e81b1d6cb72355275d456cad1475de53bdbfd",
         "7bd69f898f57a121c809d4b81412075a141cea0eb68725010f6645a00be2a988"),
        ("a2faa4a6ca56947859fea17b93a3a439c5318d357d06a66e9a8b7440eb6abaf8",
         "681c019c7eb29e039c7099a36a5b15d17ec341de8829e4db8fdd3bd5755aa668"),
        ("9d5a1c3d3687b29cc56beaafc80fb517309dbf82feb4c2999084861219eb599b",
         "508517dd11d31287f075050cc431e53bdf8f464333c0f56cfdf559f2c6186693"),
        ("fcd831d53d86f98d42c5007a9a97b3c8b1066b9677015e067456124fcb635764",
         "2f4423db1fcb7969bad6d48e7e8e7d88e257c21140f8a07479555dd0c21a75d1"),
        ("e0a042de30f2bec4f75c777241cc0081ed0ebf9ce0dd78087e25c53f82dec567",
         "40bdacf38de259f68d5c33436d6cd7396d30bb0747c994389714585bbc0f6c1a"),
        ("9946e520c3a9d50e9f32fdf446f4624000d895ede1891f7b9285b9640859f1e3",
         "77844dcc8006ca5d2bbaac9bc5b0196b9fc8835171a0e1f52e66071f697b35c4"),
    ),
}


def build_hunks(original: str, modified: str):
    """Keep two unchanged lines of context around each exact reviewed edit."""
    old_lines = original.splitlines(keepends=True)
    new_lines = modified.splitlines(keepends=True)
    matcher = difflib.SequenceMatcher(None, old_lines, new_lines, autojunk=False)
    out = []
    for group in matcher.get_grouped_opcodes(n=2):
        start_old, end_old = group[0][1], group[-1][2]
        start_new, end_new = group[0][3], group[-1][4]
        before = "".join(old_lines[start_old:end_old])
        after = "".join(new_lines[start_new:end_new])
        if not after or modified.count(after) != 1:
            raise AssertionError("ROAD100 hunk is not uniquely anchored in current source")
        out.append({"before": before, "after": after})
    return out


def generate():
    all_hunks = {}
    for name in FILES:
        old = subprocess.check_output(["git", "show", "HEAD:ai/OpexAI/" + name], cwd=ROOT).decode("utf-8")
        new = (ROOT / "ai" / "OpexAI" / name).read_text(encoding="utf-8")
        edits = build_hunks(old, new)
        if edits:
            all_hunks[name] = edits
        reconstructed = off_source(name, new, hunk_data=all_hunks)
        if reconstructed != old:
            raise AssertionError("ROAD100 projection does not reconstruct " + name)
    FIXTURE.write_text(json.dumps(all_hunks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("ROAD100 exact hunk fixture:", {name: len(ops) for name, ops in all_hunks.items()})


def _subtract_exact(name: str, source: str, edits, label: str) -> str:
    if not edits:
        return source
    if (
        name == "settings.nut"
        and "FAIR_PLAY_COURTESY = AIController.GetSetting(\"fair_play_courtesy\") == 1;" not in source
        and "function OpexLoadBusDistrictSettings()\n{\n  /* Appele au chargement, avant Start : MODE_* n'est pas encore pose. */\n  local road1yRoadOnly" in source
    ):
        source = source.replace(
            "function OpexLoadBusDistrictSettings()\n{\n  /* Appele au chargement, avant Start : MODE_* n'est pas encore pose. */\n  local road1yRoadOnly",
            "function OpexLoadBusDistrictSettings()\n{\n  /* Appele au chargement, avant Start : MODE_* n'est pas encore pose. */\n  FAIR_PLAY_COURTESY = AIController.GetSetting(\"fair_play_courtesy\") == 1;\n  local road1yRoadOnly",
            1,
        )
    present = [source.count(edit["after"]) == 1 for edit in edits]
    if not any(present):
        # Grouped hunks can contain old context that occurs multiple times,
        # and later legacy projectors can rewrite other parts of that context.
        # A fully projected source must carry no ROAD100 identifier at all.
        # Other frozen SHA checks still validate its remaining exact bytes.
        if any(token in source for token in ("ROAD100_", "road100_", "Road100")):
            raise AssertionError(f"{label} {name}: source is neither exact ON nor exact OFF")
        return source
    if not all(present):
        # One short, unchanged context region may survive BOTH projections
        # (info.nut's first ROAD100-7 group). A fully historical OFF file has
        # no ROAD100 identifiers; the frozen SHA validators then check bytes.
        if not any(token in source for token in ("ROAD100_", "road100_", "Road100")):
            return source
        raise AssertionError(f"{label} {name}: mixed or altered opt-in source hunks")
    for edit in reversed(edits):
        source = source.replace(edit["after"], edit["before"], 1)
    return source


def _subtract_road1y_b2(name: str, source: str, edits) -> str:
    """Project ROAD only; preserve unrelated RAIL hunks on one frozen merge.

    The seven skipped fixture hunks contain *only* RAIL code insertions.
    Never infer a merge from substrings, branch names, or a partial match:
    both input and output SHA checks apply to every reviewed source stage.
    """
    reviewed = ROAD1Y_B2_RAIL_MERGE.get(name)
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    approved = () if reviewed is None else (
        ((reviewed[0], reviewed[1]),) + ROAD1Y_B2_RAIL_MERGE_STAGES.get(name, ())
    )
    expected = next((out_sha for in_sha, out_sha in approved if in_sha == digest), None)
    if expected is None:
        return _subtract_exact(name, source, edits, "ROAD1Y-B2")
    if not edits or max(reviewed[2]) >= len(edits):
        raise AssertionError(f"ROAD1Y-B2 {name}: missing reviewed merge hunks")
    rail_only = set(reviewed[2])
    for index in rail_only:
        before, after = edits[index]["before"], edits[index]["after"]
        operations = difflib.SequenceMatcher(
            None, before.splitlines(keepends=True), after.splitlines(keepends=True),
            autojunk=False,
        ).get_opcodes()
        changes = [tag for tag, *_ in operations if tag != "equal"]
        if not changes or any(tag != "insert" for tag in changes):
            raise AssertionError(f"ROAD1Y-B2 {name}: RAIL-only fixture hunk changed")
    projected = _subtract_exact(
        name, source, [edit for i, edit in enumerate(edits) if i not in rail_only],
        "ROAD1Y-B2-merge",
    )
    if hashlib.sha256(projected.encode("utf-8")).hexdigest() != expected:
        raise AssertionError(f"ROAD1Y-B2 {name}: merge projection SHA mismatch")
    return projected


def off_source(name: str, source: str, *, hunk_data=None) -> str:
    # ROAD1Y-B2: exact reviewed layer above origin/master 481e7c08.
    # Older ROAD100 fixtures stay frozen and must not match that parent.
    districts = json.loads((FIXTURE.parent / "road100_bus_districts_hunks.json").read_text(encoding="utf-8"))
    source = _subtract_road1y_b2(name, source, districts.get(name))
    # ROAD100-36 is a new opt-in above all frozen historic layers. Remove
    # only its exact current hunks, then use the unchanged V35..V7 fixtures.
    v36_hunks = json.loads(V36_FIXTURE.read_text(encoding="utf-8"))
    source = _subtract_exact(name, source, v36_hunks.get(name), "ROAD100-36")
    # V35's near-first scanner and portal dispatch layer sits above the
    # frozen V34 market telemetry and V33 sparse implementation.
    v35_hunks = json.loads(V35_FIXTURE.read_text(encoding="utf-8"))
    source = _subtract_exact(name, source, v35_hunks.get(name), "ROAD100-35")
    # ROAD100-34 observes native monthly PASS units before LONG pathfinding.
    # It never participates in ranking or construction; its exact additions
    # must be removed independently before V33 and older fixed layers.
    v34_hunks = json.loads(V34_FIXTURE.read_text(encoding="utf-8"))
    source = _subtract_exact(name, source, v34_hunks.get(name), "ROAD100-34")
    # New opt-ins have separate, exact source layers. V31b's fixed-fleet
    # implementation was finalized after V32 but before V33, although its
    # historical smoke preceded V33. Do not mix those helper hunks into V32
    # or V33: older frozen ESTIM/V262 and V31 source must remain untouched.
    v33_hunks = json.loads(V33_FIXTURE.read_text(encoding="utf-8"))
    source = _subtract_exact(name, source, v33_hunks.get(name), "ROAD100-33")
    v31b_hunks = json.loads(V31B_FIXTURE.read_text(encoding="utf-8"))
    source = _subtract_exact(name, source, v31b_hunks.get(name), "ROAD100-31b")
    # ROAD100-32 was isolated against the frozen V31 motor source, not against
    # a regenerated V262 or historic fixture. Strip its exact unique additions
    # first, then the frozen ROAD100-31 / 30a / 7 and original opt-ins.
    v32_hunks = json.loads(V32_FIXTURE.read_text(encoding="utf-8"))
    source = _subtract_exact(name, source, v32_hunks.get(name), "ROAD100-32")
    v31_hunks = json.loads(V31_FIXTURE.read_text(encoding="utf-8"))
    source = _subtract_exact(name, source, v31_hunks.get(name), "ROAD100-31")
    v30_hunks = json.loads(V30A_FIXTURE.read_text(encoding="utf-8"))
    source = _subtract_exact(name, source, v30_hunks.get(name), "ROAD100-30a")
    site_hunks = json.loads(SITE_FIRST_FIXTURE.read_text(encoding="utf-8"))
    source = _subtract_exact(name, source, site_hunks.get(name), "ROAD100-7")
    if hunk_data is None:
        hunk_data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return _subtract_exact(name, source, hunk_data.get(name), "ROAD100")


def generate_site_first():
    """Initial ROAD100-7 review only: derive its delta from old, frozen opt-ins."""
    old_hunks = json.loads(FIXTURE.read_text(encoding="utf-8"))
    new_hunks = {}
    for name in FILES:
        baseline = subprocess.check_output(
            ["git", "show", "HEAD:ai/OpexAI/" + name], cwd=ROOT
        ).decode("utf-8")
        before_new = baseline
        cursor = 0
        for edit in old_hunks.get(name, []):
            # The original reviewed fixture has one short unchanged context
            # block (candidates.nut) repeated elsewhere. Diff groups are
            # ordered; forward-apply the first occurrence AFTER the preceding
            # group rather than rewriting the old historical fixture.
            pos = before_new.find(edit["before"], cursor)
            if pos < 0:
                raise AssertionError(f"{name}: existing historic hunk cannot be applied")
            before_new = before_new[:pos] + edit["after"] + before_new[pos + len(edit["before"]):]
            cursor = pos + len(edit["after"])
        current = (ROOT / "ai" / "OpexAI" / name).read_text(encoding="utf-8")
        edits = build_hunks(before_new, current)
        if edits:
            new_hunks[name] = edits
        if _subtract_exact(name, current, edits, "ROAD100-7") != before_new:
            raise AssertionError(f"{name}: new opt-in projection did not restore prior source")
    SITE_FIRST_FIXTURE.write_text(
        json.dumps(new_hunks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("ROAD100-7 exact additions:", {name: len(hunks) for name, hunks in new_hunks.items()})


def off_bytes(name: str, source: bytes) -> bytes:
    return off_source(name, source.decode("utf-8")).encode("utf-8")


if __name__ == "__main__" and sys.argv[1:] == ["--generate"]:
    generate()
elif __name__ == "__main__" and sys.argv[1:] == ["--generate-site-first"]:
    generate_site_first()
