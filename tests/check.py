# prepare <game> <copy>: a copy of the game's database with the installed car packs' gearbox rows in.
# verify <copy>: checks what the plugin added.
import sqlite3, shutil, os, sys, json, glob
T = "List_UpgradeDrivetrainTransmission"
def prepare(game, copy):
    src = os.path.join(game, r"GameFiles\Anthem_1.0.0.64_x64__8wekyb3d8bbwe\Mount\mediaoverride\Stripped\gamedbRC.slt")
    shutil.copyfile(src, copy)
    db = sqlite3.connect(copy, isolation_level=None); c = db.cursor()
    cols = [r[1] for r in c.execute(f"PRAGMA table_info({T})")]
    rows = []
    for f in glob.glob(os.path.join(game, "mods", "*", "database.json")):
        def walk(o):
            if isinstance(o, dict):
                if "NumGears" in o and "DrivetrainID" in o: rows.append(o)
                for v in o.values(): walk(v)
            elif isinstance(o, list):
                for v in o: walk(v)
        walk(json.load(open(f, encoding="utf8")))
    for r in rows:
        c.execute(f"INSERT OR IGNORE INTO {T}({','.join(cols)}) VALUES({','.join('?' * len(cols))})", [r.get(k) for k in cols])
        if r.get("IsStock") == 1: c.execute("INSERT OR IGNORE INTO Data_Drivetrain(DrivetrainID) VALUES(?)", (r["DrivetrainID"],))
    c.execute(f"CREATE TABLE FH2_Before AS SELECT * FROM {T}")
    print("prepared:", c.execute(f"SELECT COUNT(*) FROM {T}").fetchone()[0], "gearbox rows,", c.execute("SELECT COUNT(*) FROM Data_Drivetrain").fetchone()[0], "drivetrains")
    db.close()
fails = 0
def expect(ok, what):
    global fails
    print(("PASS: " if ok else "FAIL: ") + what)
    fails += 0 if ok else 1
def verify(copy):
    before = os.path.getsize(copy)
    db = sqlite3.connect(copy); c = db.cursor()
    n0 = c.execute("SELECT COUNT(*) FROM FH2_Before").fetchone()[0]
    n1 = c.execute(f"SELECT COUNT(*) FROM {T}").fetchone()[0]
    new = c.execute(f"SELECT DrivetrainID,Level,IsStock,NumGears,FinalDriveRatio,GearRatio0,GearRatio1,GearRatio2,GearRatio3,GearRatio4,GearRatio5,GearRatio6,GearRatio7,GearRatio8,Id,Price FROM {T} WHERE Level BETWEEN 16 AND 23").fetchall()
    print(f"gearbox rows {n0:,} -> {n1:,} (+{n1-n0:,}); file {before/1e6:.1f} MB")
    expect(len(new) == n1 - n0 and new, "every new row is a level 16..23 row")
    same = c.execute(f"SELECT COUNT(*) FROM (SELECT * FROM FH2_Before EXCEPT SELECT * FROM {T})").fetchone()[0]
    expect(same == 0, "the existing rows are untouched")
    expect(all(r[2] == 0 for r in new), "none of them is marked stock")
    expect(all(r[1] == 15 + r[3] - 1 for r in new), "Level = 15 + forward gears")
    expect(all(2 <= r[3] <= 9 for r in new), "1 to 8 forward gears (the game's cap is NumGears 9)")
    bad = 0; orderbad = 0
    for r in new:
        n = r[3] - 1; rs = r[6:14]
        if not all(x > 0 for x in rs[:n]) or not all(x == -1 for x in rs[n:]): bad += 1
        if any(rs[i] <= rs[i + 1] for i in range(n - 1)): orderbad += 1
    expect(bad == 0, "used gears are positive, unused ones -1 as the game has them")
    expect(orderbad == 0, "each gear is shorter than the one before")
    stock_rows = {r[0]: r for r in c.execute("SELECT DrivetrainID,NumGears,GearRatio1,GearRatio2,GearRatio3,GearRatio4,GearRatio5,GearRatio6,GearRatio7,GearRatio8 FROM FH2_Before WHERE IsStock=1")}
    def progressive(g):
        return len(g) < 3 or g[0] / g[1] > g[-2] / g[-1]
    prog = 0
    for r in new:
        n = r[3] - 1
        own = stock_rows[r[0]][2:2 + stock_rows[r[0]][1] - 1]
        if not progressive(r[6:6 + n]) and progressive(own): prog += 1
    expect(prog == 0, "every gearbox is progressive (big steps low, small near the top), unless the car's own isn't")
    # The same numbers as the Python twin the in-game tests use
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from twin import spaced as twin
    off = 0
    for r in new:
        sr = stock_rows[r[0]]; n = r[3] - 1
        want = twin(list(sr[2:2 + sr[1] - 1]), n)
        if any(abs(r[6 + i] - want[i]) > 1e-6 * want[i] for i in range(n)): off += 1
    expect(off == 0, "every gearbox matches the Python twin of the formula")
    rule = int(os.environ.get("SHIFT_RULE", "1"))
    shift_rows = c.execute(f"SELECT t.DrivetrainID,t.NumGears,t.GearShiftTime,b.NumGears,b.GearShiftTime,(SELECT MIN(GearShiftTime) FROM FH2_Before r WHERE r.DrivetrainID=t.DrivetrainID AND r.Level=3 AND r.IsStock=0) FROM {T} t JOIN FH2_Before b ON b.DrivetrainID=t.DrivetrainID AND b.IsStock=1 WHERE t.Level BETWEEN 16 AND 23").fetchall()
    wrong = 0
    for d, n, got, bn, bshift, race in shift_rows:
        if n <= bn or rule == 0: want = bshift
        elif rule == 1: want = bshift * (bn - 2) / (n - 2)
        else: want = race if race is not None else bshift
        if abs(got - want) > 1e-6: wrong += 1
    expect(wrong == 0, f"shift times follow rule {rule} on every gearbox ({len(shift_rows)} checked)")
    f430 = c.execute(f"SELECT t.NumGears-1,t.GearShiftTime FROM {T} t WHERE t.DrivetrainID=(SELECT DrivetrainID FROM List_UpgradeDrivetrain WHERE Ordinal=1022 AND IsStock=1) AND t.Level BETWEEN 16 AND 23 ORDER BY 1").fetchall()
    print("   the F430's new gearboxes (forward gears, shift time):", [(g, round(s, 4)) for g, s in f430])
    stock = {r[0]: r for r in c.execute(f"SELECT DrivetrainID,NumGears,FinalDriveRatio,GearRatio0,GearRatio1,GearRatio2,GearRatio3,GearRatio4,GearRatio5,GearRatio6,GearRatio7,GearRatio8 FROM FH2_Before WHERE IsStock=1")}
    kept = same_count = 0
    for r in new:
        s = stock[r[0]]; n = r[3] - 1; fw = s[1] - 1
        if n == fw: same_count += 1
        if abs(r[4] - s[2]) > 1e-9 or abs(r[5] - s[3]) > 1e-9: kept += 1
        if n >= 2 and (abs(r[6] - s[4]) > 1e-6 or abs(r[5 + n] - s[3 + fw]) > 1e-6): kept += 1
    expect(kept == 0, "final drive and reverse are copied; first and top gears are the car's own")
    expect(same_count == 0, "no car gets a copy of the gear count it already has")
    ids = [r[14] for r in new]
    expect(len(set(ids)) == len(ids), "ids are unique")
    labels = c.execute("SELECT Level,Name,Description,IconPath,id FROM Upgrades WHERE TypeId='15' AND Level BETWEEN 16 AND 23 ORDER BY Level").fetchall()
    expect(len(labels) == 8 and all(l[3] for l in labels), "8 labels, with the game's icon")
    expect(all(l[1].startswith("_&") and int(l[1][2:]) >> 16 == 0x7091 and int(l[2][2:]) >> 16 == 0x7091 for l in labels), "named through the game's Upgrades string table")
    print("  ", labels[0][:3], labels[7][:3])
    car = c.execute("SELECT DrivetrainID FROM List_UpgradeDrivetrain WHERE Ordinal=424 AND IsStock=1").fetchone()
    expect(c.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='FH2_GearboxUpgradesReady'").fetchone()[0] == 1, "the marker is there")
    per = c.execute(f"SELECT MAX(n) FROM (SELECT COUNT(*) n FROM {T} GROUP BY DrivetrainID)").fetchone()[0]
    print("most rows on one drivetrain:", per)
    expect(per <= 16, "at most 16 rows a drivetrain (Enhanced Tuning's new limit)")
    s = c.execute(f"SELECT NumGears,GearRatio1,GearRatio2,GearRatio3,GearRatio4,GearRatio5,GearRatio6,GearRatio7,GearRatio8 FROM {T} WHERE Level=23 AND DrivetrainID=(SELECT MIN(DrivetrainID) FROM {T} WHERE Level=23)").fetchone()
    print("an 8-speed:", s)
    db.close()
    print("failed:", fails)
    return 1 if fails else 0
if sys.argv[1] == "prepare": prepare(sys.argv[2], sys.argv[3])
else: sys.exit(verify(sys.argv[2]))
