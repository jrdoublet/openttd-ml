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
        "9f7a522edbfe2a69411113be6d0de489ab8b472fc42f5553f72955273f7ae598",
        "96f7dc5d79a483af163e3d3f635f0a92d1d77a3ded645cd66405c0e31e0c0ae4",
        (1,),
    ),
    "info.nut": (
        "a91f430ec17fa802db2b1fb02b6498a6dcaed31662073abff6685a63abb44342",
        "d96fce4110576d30b5f45decda3ff6ddd342faeaf346794b5e663eebba02ecbd",
        (0,),
    ),
    "settings.nut": (
        "31e522e2c0684bef48b4f38ec3fd9d906b961af497eb70c1b484b3791f6bb326",
        "1716a28bbe2ec6a0d5d64e6036df3c62e6c164ef4a94aa697b4132b19f10243b",
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
        ("b5b1ec86bfb2803f2c8df7b67a133a24aa6d85a43830db4145213a0f5b5c04a4",
         "622796e810d1c6afcb5861a980caaea1a9024a16b84e7ff1c2f9524d7c20154b"),
        ("8a41b1da499c9604a50913d5697530925c8c32a7ce6b078ca9338bf37a4c0b33",
         "ee351823e319d471d7b53146bb1ac2341ba1119081b23e5ebbcb3ce63fa2c89f"),
    ),
    "globals_pre.nut": (
        ("95287db807334e84c5a1146a7d2ca446d6c464aa9daf6cd2b55cd7d76d19ad3d",
         "8ff485029940bed662ea10a539e1c47a94b0decda19de2c3954020b09a1dbca7"),
        ("c6861e400454c652fcf150e9148be6d96d6bf7c370df15009bfedf9732bd90e9",
         "09844bbed074c149fca50293bc9bf9e75f19f3ada9cb0f533a585f6bcf9a6b57"),
        ("42d7708dc890be6adbf5936c4879075ece39a030a777318edcaaa77b719a86d0",
         "fe3ffab63749bc618f3ad46c73ed5bbf193727e94ef5c52a1ff13d5a6e5838cf"),
        ("d0548c85cd11d62de13e4eb1566088d77a15ab6490b3a30a01fb27eda3110424",
         "a5fac92a00c72cdcb7fb091bab51ef14092f76fd92debe759c02986970ee0e1d"),
        ("39f211849e7f291f76466c620526243194969f490b395c0cda8757f753b38417",
         "576c80b9b23cf8d2a652d22ffd9ffcb0f88670a3c63d49229ae631e2bd4130a9"),
        ("166208c952b06c55fd3b4b27bfcac22b0543cfebd16a93645ad9cb21fcff2048",
         "45052446bc784c2a7da1d0ab2cb6d7fb88a5e598549bd3471624bb41542bac0a"),
        ("22295625b0bbb8ffb226e46df8b2b2ab9caf28c55d2a62054581b42705ffc323",
         "f984c78ef25566d83bff3d91af2e2ffcc0ae0df695252ae752f3b760f48e75ea"),
        ("14092ce902f853a19d77980467627b727cf6e32e9d4bc094c8a9145e296bdac9",
         "1fb4a5e52ac92b5db12c7b5d06107a880437b99352375124d60bb8b0f55e7c9f"),
        ("f914642ec34f9347436c1b4cfbebfc7eecd8ae38940dae65af12bdd7dde6dc46",
         "9d6e7a5191d0933f97e83c7712cbd5f7cb6d6198ef742d91688e3586d8052910"),
        ("bf786d7685278d8fa4bce5dc6b141cf0cf45b86753db955073e1b68a5ff91dd7",
         "883b875cf3b7f0f630ccf8ae4acf3d3074fd9fc97438312e5f0d0cc5ee0ff0d4"),
        ("352d7a9db8c1b367e382fbf52c20e1fd0f8105e7a713fa8a86c4263b8fbf537b",
         "39654f30b7e1e112c9cccb2adbca7b85679b5e99d17bb2a013075b58a0a8345e"),
        ("b82fa06acecfbeb8d1154ab89dd590ac7527c7c82bec13cbcf8a4cac2f685494",
         "0a0104b232f8b037f3999637aa71b2af48600c919be8202ba9e495a8de4f49d2"),
        ("14e4b9b83ebee2b2b51d60fdfad0a572bf8cd5bdd04befe832b48649084a0c6e",
         "ed3cf5624070dce0e68915545f724c6d474911da595813522c3847eff08654f5"),
        ("bda552a90cc442693ef38fd015a7b9df78c94fa5ac5fbede269665d117469275",
         "b6a47d039458fbceba0b1348bb40f214e4aa1473d3119a285da3ef4c1c0d8acf"),
        ("2c73135006dbf95ee1b2151846434a516e423703d8cc00dcf6fa576a6dd586a2",
         "944e9e95ebf9e37ffc7c88e3d13e36cfbc6e4e8b318af974a022e4017798f80d"),
        ("6f769fcc4c641fd26964c388ef81af4f448f39ce20edfa7aaf2cd9e20b8f9209",
         "4fb40966b1c27aa8ab615b6bb047061f8c0e8c556e9171bb37290cd0b3f6390f"),
        ("441a9528e465b0390dc985a322db92f8f8d78991e744fb196f275d798aef8015",
         "6b76ff6f36731fe402e91072387b5f745a58158191341ea5051e953ab5a8c90b"),
        ("f9333488da61b18ce4c8e1aa1858948173d017f38df2ca99c5e08f97ef437f8d",
         "6bd1a2b73af1e6afbaf1886d51a41bc2637da7541a5f7532272391eda07616c3"),
        ("6278d05f64d59d601fd58a0917cdb2c4b9e876e01662fc2d5139a23061b13b25",
         "c7c29bfac2806d8fd03774644af91b83be08bb0aaa948f2063971a37622b10a2"),
        ("2c2efec5cebb836673163aed783e5e7a4137eb0c82726aec4f697d14d38a635d",
         "121228d4c252951b84e3164b58fd4c3033e642a1507c0a31844adbaded720389"),
        ("881d3fca6cde08924dacc4d4b6511431114cb8692e28186112a7e6a5bd25fafb",
         "18a9f97a6b2faf8e60dec822961821c5814ffaefac63a68465cc4c7b10d83591"),
        ("4ea00886294394c2347923c47b3e55bd0d6d6b07ed5b72bd27b9299590bbc1ba",
         "139aa9db8b54d04ec32b74efea69ec60a7112af7312e690e44b64612a03ca12d"),
        ("bee9cd52c55ae3a9b14b7685a384db7bd3cde2737be22e5f876461014bcdbce1",
         "cfceaff01fa423b6bfd1248def104ad4683005636b1e807c81e0f4ae7fd9f964"),
    ),
    "info.nut": (
        ("1fbdac0c3e35ee9812033b7456620b512f7b641cf780ab1c74ff0f1dcc0e3e63",
         "46b702bbe37532bc8212af5058147caa5b12cce41ac427f3a3b58d244907d19f"),
        ("86d67cac63199b4a1ab267acb533513b1f2ab5391558988351eba0e7efc261aa",
         "8bf5ca75fe04815effbfa632386adc2118bd78b2147e951a8a067505eb817bdc"),
        ("ebb95bf341a59e795c542dc3502d7105f2f9f3413daabd753467230d4dc97ffc",
         "65c458f5290ceb7c0d36e706bf25a9ac796e6cb833ad534242786868fafd6057"),
        ("0e6e6e30aaae1b814dc8afbaad515347e2dc05aea133cd12983a7abc1fce26f1",
         "db4e98d70522a49ae3242441b5479e22ae3422bc0eca772677da37f8aa04f0d2"),
        ("141a14576a3fc1837acd0c5ba146abffb0fe3ada740b6dac2b744f44445a32a8",
         "394091141da842f541e9bce5b86474c4571b8de65a4eba2c24b2d557643eacaf"),
        ("ea9f364645f73a8a1b9817d479cd7ede2623680148524352e97c4752ffba9ffd",
         "225adee94dbb54fd8318cf8d55d08ca9991e9c3412f98666bdb956842682ef0b"),
        ("505d709a7fa7a4340a984503ac26ea993da13ca42863836ad1796bf5d79cb46c",
         "0e9068acb705de9c03a6b4ba9adf1dea1135d2e2f69687baaf1324c07aa25dcc"),
        ("dea79bb97b5153aab3fe91e659451c6021ac30660846342cf1e0ae4382877613",
         "9373cb046c9328d93e17e00bca55a2052af26215ceaf886721f4d81f366c63ea"),
        ("6f4107a4c5100fcfabb2d9caf8d4f204101fd6a92534b72c2a9d102da71dff11",
         "5e3c1c006151e853582f423352cc8d431474e8aa439fabb5bce677e5e88252b0"),
        ("9d2e28e8b93e7da7f855b124e971b2567c05171ff3f5af713561fc1d1834a872",
         "a82cd93490750053d9549474e92c3e3d461fb95e37345d7c214f00b7164e1953"),
        ("40669104c16556e1f4d3bd6f84475c921054fd1f719acd73222da10d79d79db9",
         "106b85f063d46f351cc0e19bbe396501d63bfe6d35291a8e135d6754218e8364"),
        ("053c32b60ea03c4a857644ac59296cb0a8b0c18df67a7a5e84317132a9e6eecd",
         "8947c5a2ced846591668fc76f16ce3301fd446d435a469f0de1d349c6bc3656d"),
        ("92870d608bf4a6e575c142beca2fd24783d419a75a05e1e22b6801c498633d76",
         "5c65cbe59ffa26947020c592077b7492048af593e8ca674fcbcddeef289dcbe6"),
        ("82904cb6b144ae9c04038cd6ecdc8b14e27709040062c2a836b05061bce746cc",
         "5e641f5afc6fa1f688b069ca231ba67545fa0e050b6aa6c887ff37478bfda55f"),
        ("dafa4f4bade53cf45f933ac02823e2ec2049b908f7813235b5ed3630b13fc0e6",
         "ad775bca37577a38fb3744fe3f9c98783bc21d0aaa85e9e8131b2c23ecddb547"),
        ("fe97429b70549e1307dae0ae9c1756952a7badc7e9ad352f0ad6285d92be62e0",
         "6a8e31605c0c4ab871bd4e01984414d4bd624ffcb0e9032b34fe509d430bab6d"),
        ("851ef126ab645d062200e4f9fec36db07f4860deb3cd586c3a2474c3fb354173",
         "b69cf8b001c43673dabc21efac47c7e135a98168906589c0096f57b263674f53"),
        ("b33291f5ec31fa4d997a1064f683eef934de8368d93064ab32a331f9c7e82d69",
         "fcf484d9b56209b52b594b6d744179a733ca7e0af141466472f27f1d332b5280"),
        ("cc954b7037ba9cc4b3682a9b1c6fc496c8fd6368976bca385610e47cdca59668",
         "d6790629a00b3b2d997ee480c876d1687cacb490ee64989a50101bc9be2a6f55"),
        ("bd40d2fa9d7dd26075d09b355dfc2bdd526242d98f621e787ce72f342723eb8f",
         "c33a4a12fa00eebbd76c947b7f435f4bdb64e2ca208033a927db55dd32facaa6"),
        ("833c712d9a15ab0bd714b4f9ae6fc7c6858f0163c5ead5bcace290467299b2e2",
         "78f72017c7a78f86b2ddc5f1dc43605219cd89a4c168722350e7d415d56ebaf4"),
        ("38710d82cdc348af734a72e2da3d42d85fea4b4123c9233f1750703073a7fc10",
         "9c83ea7ba0f3aa71e0c8eb8fdc1341817d2ad490a9891844d3de2e1761ba01fb"),
        ("a73354b15c9bb58470eba5f983815e2442b3f99c81a5caf2bffd996999712be6",
         "861ade126872a466574882f4dd212bd060ed9ec99d8b79bb1233770a806b3b75"),
    ),
    "settings.nut": (
        ("4ba30a2a9a44059be4f33da8906bf7c289be24cb49376563616ce487a111f483",
         "5739b3a18c226c969200f142dfa5e173002dec76ff094090b3c120f2fc597bb2"),
        ("12ff68193bd638c2f4eb5139151fe872bb05fb163bda1a299610e3481ae1e2e3",
         "5a9c5cddcd059ba8b8679f949d19d75d8c5213427d60375a9421a17dbe362567"),
        ("1dadbfebb825771eec820582830227c6b2d29580c2eed6f392517f731d5eb02f",
         "4ac2ffaed7f5a5c7236591422a5154162570d649c48ff36d8db34384dcd20ff9"),
        ("32542fef11a2bad6fbc7716a4e07a52758e7a2e358af172d2b43c3ee4a0a59fc",
         "e9a77ce85ffb1a8b552c2022b3aa1f6abf53797c9813a09b62118d9840de1ec4"),
        ("3ef68a177f0e75f37d8801fb4b5a978c43ed7f28c951dcfe93e5750b6988550e",
         "11bbc0f35b691dbeb3606c54efe05757f0105692f7e445e7a0a48a13b53a9de4"),
        ("211845a3ef640b9dab17ac9db8cbdf754a1b28f9335e127ea17853182c334b4f",
         "802e87045cc7eeae9b065b3f9bd07aa6f35ebd2b0b3d7ae9c09169f18175dd39"),
        ("98024603f7c926a881cc3add09371e312ff8ac235204386a79ff86c7cc2ea9d1",
         "15b84d1e226bde237284cb1339d7ea88f46dbc0069a4f08687c1da1a2194dc8f"),
        ("91a5180fea0be5e719e6cb3710a1165dba6939bc8274169429654b0bca73837c",
         "5a8e52db0acfb1b69ce31b2cd18553d1c6e80d9086d472ef165e3ab3250bc7e0"),
        ("774e9295d11ddc678d8f174b0d2fb86b4f99f2ad0a1966a7cd9a75802c473f65",
         "145e22d3a84a366cb13d0378441f4a7bd75ee6965089c64c567b87dbed07e948"),
        ("d887b324868c577b324f419dd2a77cb3e71705ff8e5a7491dc4d00a32c77aafb",
         "7adaafc4e992b2ef878723fdb89c05670e4116a9f63e5537830c7eecc88d64b0"),
        ("76473de8986994623e07e9193617b150a4ec37f11a88dcf670a6e9e8ec840fd8",
         "06e5a84e4346d43abcd5aa00b1799eaa86c13dde1bf7d4afc394feb629ee0d7a"),
        ("135d2f89c3e29ffd6c0e9858d7709742155c4be1136664dbfea87bcde2974aed",
         "9ba8957d73950db2895b53bc4fc666f4d02f489a98474f4e710aca595eb7956e"),
        ("18d1e242def0a4b1b5a92f27899582843df371d40b6d4a826f5b75e4ad17cbc3",
         "90ada168c73d67717985e107ac0459f4aadde508d3b898ff04348b9f7df57045"),
        ("a0553bb52859e143ab678ff0701abfc8e9f7fa53317c9e6bea94cf350db8cbf6",
         "1f8ff8ab21d2c60e13f9e202df5a7f92eb2c06b313f3875c4a53fdea6dd8d868"),
        ("28b30493fe4b8f0e2f0b1ec7b8e1a6ac9d3bc08547d812419b9680496bbd743f",
         "bf22d406853ccfbe5f3e278d63adbeed4802cc775de175028f9fa8caadbc0b48"),
        ("138ef0dfcee207b3a0d07b05b74a84d3bd4c282cccaa992b194ef735f489b79d",
         "d45402aca5f9e0ec37417490a900b34a6c71876bd1fc0083b66baf27e3566fab"),
        ("61110d9b52dc41f5ce2db3591dbe6a32455f1b36f60f0854dd5e53e25cd1029d",
         "412fb7ef9fa3391d598388d8294b1bc14d961e8091cc4802ae48d2548f4117e8"),
        ("dbab33efc9e96bce8a82e134f36468149e7fc041b4a6a4a1864848821e552716",
         "1b41eeb87b03b0a0d3c029a0b48d0c6f525828b145176471cdcad84f9913edec"),
        ("18d79e572084c81c557427d0e025bb89d5a83d5a2d6c906d681c6b6b8b9ba446",
         "938a4bfa8b3c584bf3912b37a8ba1c1fde3ba7bb488a87851ff7ebd8f64d6416"),
        ("cd282ee80fed2227f1583fcacf230543c720c2fc29cd4cce951f974330d1e994",
         "591e3ce992a6f0ea595efd80a08a82ff40a02255de0d02141617f0b814379bbc"),
        ("11ba7da2761398308c3975f898cbc94b74b298f22ba1f692cef9023a405da5c3",
         "4e26032ab4e64b93870afbf05055cda1b9675c8f49f2302819a38fd6ed267714"),
        ("373eac95131d8f3c932614c0bb2975e31dd34b227f483b162195ebfa5e2c5f01",
         "d170a904c3cfd1891a1e07a7774ccb5aecdadd20b93988007f80de1a2b085c34"),
        ("38209a59ce92abd0c8c151decec5bedd0397d3d4163796ee9871cc9d529ef4d8",
         "fd9383ac1f8c2d4c59dd3916dbc8eb9330c442305acb442f3af443727530ec48"),
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
