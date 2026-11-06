// Gearbox Upgrades: gearboxes with 1 to 8 forward gears as upgrades for every car.
//
// An Extra Options plugin. Once per merged database, each car's stock gearbox row gets a copy for
// each number of forward gears it doesn't have already, with a label row per number. They're
// ordinary rows, so the Upgrades screen lists them and the garage saves them like any other part.
//
// The game's reader takes NumGears (reverse + forward, capped at 9: game+0x10647e6) and that many
// of GearRatio0..8, so 8 forward gears is the most a row can hold. A gearbox's Level above 1 makes
// its ratios tunable (game+0x10647d1), so these all are.
//
// Ratios: the car's own first and top gears stay, so launch and top speed stay about where they
// were, and reverse and the final drive are copied. The gears between follow the curve real gearboxes
// do, big steps low down and small ones near the top: from first to top, log(ratio) falls off as
// (1 - x)^SPACING, the median fit over the 478 stock gearboxes of the game and the ZS car packs
// (tests/spacing.py). On top of that goes half of how this car's own gearbox differs from the curve,
// followed smoothly (monotone cubic) to the new gears' places: its own character, without copying the
// noise in it. Rebuilding real gearboxes with a gear taken out, that's as close as the curve alone and
// closer in the worst cases (tests/spacing_methods.py); Jante's textbook series, by contrast, puts
// gears out of order when stretched to 8. One gear sits halfway between first and top.
//
// Nothing here touches a file: it's the merged database in memory. A car saved with one of these
// needs this mod installed, as it does with any added part.
#include <math.h>
#include <stdarg.h>
#include <stdio.h>

#include "fh2_plugin.h"

#define GEAR_TABLE "List_UpgradeDrivetrainTransmission"
#define MARKER "FH2_GearboxUpgradesReady"
#define SPACING 1.38
#define QUIRKS 0.5  // how much of the car's own difference from the curve it keeps

// Shift time of a gearbox with more gears than stock (fewer keeps the stock time):
//   0 the stock gearbox's own
//   1 quicker in proportion, so going from first to top takes as long as stock did
//   2 the car's own Race transmission's (game levels: stock ~0.16 s, Sport ~0.08, Race ~0.04)
#ifndef SHIFT_RULE
#define SHIFT_RULE 1
#endif

enum {
    SQLITE_ROW = 100, SQLITE_DONE = 101,
    MAX_GEARS = 8,
    MAX_BASES = 8192,
    LEVEL_BASE = 15,            // Level = 15 + gears: 16..23, past the game's 0..4 and below Extra Options' 24+
    ID_BASE = 0x30000000,       // above the game's and the mods' ids; Extra Options' swaps use 0x20000000 up
    PRICE = 2000,
    // Names are string table references: "_&" + (table << 16 | entry). 0x7091 is the game's Upgrades
    // table, where its own gearbox names are; strings.json fills these entries.
    STRING_TABLE = 0x7091,
    NAME_ENTRY = 65300,         // + gears
    DESCRIPTION_ENTRY = 65320,  // + gears
};

typedef struct {
    int64_t row, drivetrain;
    int forward;
    double shift;  // GearShiftTime, s
    double ratio[MAX_GEARS + 1];  // [1]..[8], in the row's own units
} Base;

static void (*log_utf8)(const char *);
static Base bases[MAX_BASES];

static void logf_line(const char *format, ...) {
    char line[300];
    va_list args;
    va_start(args, format);
    vsnprintf(line, sizeof line, format, args);
    va_end(args);
    if (log_utf8) log_utf8(line);
}

static int run(const FH2PluginDatabaseFrame *db, const char *sql, int64_t *first_column) {
    void *statement = NULL;
    const char *tail = NULL;
    if (db->prepare(db->database, sql, -1, &statement, &tail) != 0 || !statement) return 0;
    int result = db->step(statement);
    if (result == SQLITE_ROW && first_column) *first_column = db->column_int64(statement, 0);
    while (result == SQLITE_ROW) result = db->step(statement);
    return db->finalize(statement) == 0 && result == SQLITE_DONE;
}

// Each drivetrain's stock gearbox, as long as it has a first and a top gear to work from.
static int read_bases(const FH2PluginDatabaseFrame *db, unsigned *count) {
    static const char sql[] =
        "SELECT rowid, DrivetrainID, NumGears, CAST(ROUND(GearRatio1*1e9) AS INTEGER), CAST(ROUND(GearRatio2*1e9) AS INTEGER), "
        "CAST(ROUND(GearRatio3*1e9) AS INTEGER), CAST(ROUND(GearRatio4*1e9) AS INTEGER), CAST(ROUND(GearRatio5*1e9) AS INTEGER), "
        "CAST(ROUND(GearRatio6*1e9) AS INTEGER), CAST(ROUND(GearRatio7*1e9) AS INTEGER), CAST(ROUND(GearRatio8*1e9) AS INTEGER), "
        "CAST(ROUND(GearShiftTime*1e9) AS INTEGER) "
        "FROM " GEAR_TABLE " WHERE IsStock=1 AND NumGears BETWEEN 3 AND 9 AND FinalDriveRatio>0 AND GearRatio1>0 "
        "AND DrivetrainID IN (SELECT DrivetrainID FROM Data_Drivetrain) ORDER BY DrivetrainID";
    void *statement = NULL;
    const char *tail = NULL;
    if (db->prepare(db->database, sql, -1, &statement, &tail) != 0 || !statement) return 0;
    unsigned n = 0, skipped = 0;
    int result;
    while ((result = db->step(statement)) == SQLITE_ROW) {
        if (n == MAX_BASES) break;
        Base *b = &bases[n];
        b->row = db->column_int64(statement, 0);
        b->drivetrain = db->column_int64(statement, 1);
        b->forward = (int)db->column_int64(statement, 2) - 1;
        for (int g = 1; g <= MAX_GEARS; ++g) b->ratio[g] = (double)db->column_int64(statement, 2 + g) / 1e9;
        b->shift = (double)db->column_int64(statement, 11) / 1e9;
        if (b->ratio[b->forward] > 0 && b->ratio[1] > b->ratio[b->forward]) ++n;
        else ++skipped;
    }
    int finished = db->finalize(statement) == 0 && (result == SQLITE_DONE || n == MAX_BASES);
    if (skipped) logf_line("GEARBOX UPGRADES: %u stock gearboxes skipped: no first and top gear to work from.\r\n", skipped);
    *count = n;
    return finished;
}

static int add_labels(const FH2PluginDatabaseFrame *db) {
    char sql[700];
    for (int gears = 1; gears <= MAX_GEARS; ++gears) {
        int64_t changed = 0;
        snprintf(sql, sizeof sql,
                 "INSERT INTO Upgrades(id,TypeId,IsException,Name,Level,Description,IconPath,ImagePath) "
                 "SELECT %d,'15',0,'_&%u',%d,'_&%u',IconPath,ImagePath "
                 "FROM Upgrades WHERE TypeId='15' AND Level=2 AND IsException=0",
                 ID_BASE + gears, ((unsigned)STRING_TABLE << 16) | (unsigned)(NAME_ENTRY + gears), LEVEL_BASE + gears,
                 ((unsigned)STRING_TABLE << 16) | (unsigned)(DESCRIPTION_ENTRY + gears));
        if (!run(db, sql, NULL) || !run(db, "SELECT changes()", &changed) || changed != 1) return 0;
    }
    return 1;
}

// Monotone cubic (Fritsch-Carlson) through (xs, ys), n points, at x. Mirrored in tests/spacing.py.
static double pchip(const double *xs, const double *ys, int n, double x) {
    double h[MAX_GEARS], d[MAX_GEARS], m[MAX_GEARS + 1];
    if (n < 2) return n ? ys[0] : 0;
    for (int i = 0; i < n - 1; ++i) {
        h[i] = xs[i + 1] - xs[i];
        d[i] = (ys[i + 1] - ys[i]) / h[i];
    }
    m[0] = d[0];
    m[n - 1] = d[n - 2];
    for (int i = 1; i < n - 1; ++i) {
        if (d[i - 1] * d[i] <= 0) {
            m[i] = 0;
        } else {
            double w1 = 2 * h[i] + h[i - 1], w2 = h[i] + 2 * h[i - 1];
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i]);
        }
    }
    for (int i = 0; i < n - 1; ++i) {
        if (x < xs[i] || x > xs[i + 1]) continue;
        double t = (x - xs[i]) / h[i], t2 = t * t, t3 = t2 * t;
        return (2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i] + (-2 * t3 + 3 * t2) * ys[i + 1] +
               (t3 - t2) * h[i] * m[i + 1];
    }
    return x > xs[n - 1] ? ys[n - 1] : ys[0];
}

// Gear g of a `gears`-speed made from this car's stock gearbox. See the top of the file.
static double spaced(const Base *b, int gears, int g) {
    double first = b->ratio[1], top = b->ratio[b->forward], span = log(first / top);
    double xs[MAX_GEARS], quirk[MAX_GEARS];
    if (gears == 1) return sqrt(first * top);
    if (g == 1) return first;
    if (g == gears) return top;
    for (int i = 0; i < b->forward; ++i) {  // where the car's own gears sit, against the curve
        xs[i] = (double)i / (b->forward - 1);
        quirk[i] = log(b->ratio[i + 1] / top) / span - pow(1.0 - xs[i], SPACING);
    }
    double x = (double)(g - 1) / (gears - 1);
    return top * exp(span * (pow(1.0 - x, SPACING) + QUIRKS * pchip(xs, quirk, b->forward, x)));
}

static int add_gearbox(const FH2PluginDatabaseFrame *db, const Base *b, int gears) {
    char sql[1600], ratios[8][32], shift[200];
    if (gears <= b->forward || SHIFT_RULE == 0)
        snprintf(shift, sizeof shift, "GearShiftTime");
    else if (SHIFT_RULE == 1)
        snprintf(shift, sizeof shift, "%.9g", b->shift * (b->forward - 1) / (gears - 1));
    else
        snprintf(shift, sizeof shift,
                 "COALESCE((SELECT MIN(GearShiftTime) FROM " GEAR_TABLE " WHERE DrivetrainID=%lld AND Level=3 AND IsStock=0), GearShiftTime)",
                 (long long)b->drivetrain);
    for (int g = 1; g <= MAX_GEARS; ++g) {
        double value = g <= gears ? spaced(b, gears, g) : -1.0;  // -1: what the game has in a gear a gearbox doesn't have
        snprintf(ratios[g - 1], sizeof ratios[0], "%.9g", value);
    }
    snprintf(sql, sizeof sql,
             "INSERT INTO " GEAR_TABLE "(Id,DrivetrainID,Level,IsStock,ManufacturerID,MassDiff,Price,MomentInertia,GearShiftTime,"
             "FinalDriveRatio,NumGears,GearRatio0,GearRatio1,GearRatio2,GearRatio3,GearRatio4,GearRatio5,GearRatio6,GearRatio7,"
             "GearRatio8,CVTShiftTime) "
             "SELECT %lld,DrivetrainID,%d,0,ManufacturerID,MassDiff,%d,MomentInertia,%s,FinalDriveRatio,%d,GearRatio0,"
             "%s,%s,%s,%s,%s,%s,%s,%s,CVTShiftTime FROM " GEAR_TABLE " WHERE rowid=%lld",
             (long long)ID_BASE + b->drivetrain * 16 + gears, LEVEL_BASE + gears, PRICE, shift, gears + 1, ratios[0], ratios[1], ratios[2],
             ratios[3], ratios[4], ratios[5], ratios[6], ratios[7], (long long)b->row);
    return run(db, sql, NULL);
}

__declspec(dllexport) BOOL WINAPI FH2PluginDatabaseUpdate(const FH2PluginDatabaseFrame *db) {
    int64_t marked = 0;
    unsigned count = 0, added = 0;
    if (!db || db->size < sizeof *db || !db->database || !db->prepare || !db->step || !db->finalize || !db->column_int64) return FALSE;
    if (!run(db, "SELECT COUNT(*) FROM sqlite_master WHERE name='" MARKER "'", &marked)) return FALSE;
    if (marked) return TRUE;
    ULONGLONG started = GetTickCount64();
    if (!read_bases(db, &count) || !count) {
        logf_line("GEARBOX UPGRADES: couldn't read the stock gearboxes (%u found); nothing added.\r\n", count);
        return FALSE;
    }
    if (!run(db, "SAVEPOINT gearbox_upgrades", NULL)) return FALSE;
    int ok = add_labels(db);
    if (!ok) logf_line("GEARBOX UPGRADES: couldn't add the labels.\r\n");
    for (unsigned i = 0; i < count && ok; ++i)
        for (int gears = 1; gears <= MAX_GEARS && ok; ++gears) {
            if (gears == bases[i].forward) continue;
            ok = add_gearbox(db, &bases[i], gears);
            if (ok) ++added;
            else logf_line("GEARBOX UPGRADES: couldn't add %d gears for drivetrain %lld.\r\n", gears, (long long)bases[i].drivetrain);
        }
    ok = ok && run(db, "CREATE TABLE " MARKER " AS SELECT 1 AS Version", NULL);
    if (!ok || !run(db, "RELEASE gearbox_upgrades", NULL)) {
        run(db, "ROLLBACK TO gearbox_upgrades", NULL);
        run(db, "RELEASE gearbox_upgrades", NULL);
        log_utf8 ? log_utf8("GEARBOX UPGRADES: rolled back; nothing added.\r\n") : (void)0;
        return FALSE;
    }
    logf_line("GEARBOX UPGRADES: added %u gearboxes for %u drivetrains in %llu ms.\r\n", added, count,
              (unsigned long long)(GetTickCount64() - started));
    return TRUE;
}

__declspec(dllexport) BOOL WINAPI FH2PluginInitialize(const FH2PluginContext *context) {
    if (context && context->size >= sizeof *context) log_utf8 = context->log_utf8;
    return TRUE;
}
