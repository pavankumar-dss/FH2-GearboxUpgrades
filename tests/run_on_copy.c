// Runs the built plugin's real database callback on a copy of the game's database (via Windows'
// own winsqlite3.dll). Usage: run_on_copy <plugin.dll> <database copy>
#include <stdio.h>
#include <windows.h>

#include "fh2_plugin.h"

static void log_line(const char *s) { printf("log: %s", s); }

int main(int argc, char **argv) {
    if (argc < 3) return 2;
    HMODULE sql = LoadLibraryW(L"winsqlite3.dll"), plugin = LoadLibraryA(argv[1]);
    if (!sql || !plugin) { printf("can't load (%lu)\n", GetLastError()); return 2; }
    int (*open)(const char *, void **) = (void *)GetProcAddress(sql, "sqlite3_open");
    int (*close_db)(void *) = (void *)GetProcAddress(sql, "sqlite3_close");
    int (*exec)(void *, const char *, void *, void *, char **) = (void *)GetProcAddress(sql, "sqlite3_exec");
    BOOL(WINAPI * init)(const FH2PluginContext *) = (void *)GetProcAddress(plugin, "FH2PluginInitialize");
    BOOL(WINAPI * update)(const FH2PluginDatabaseFrame *) = (void *)GetProcAddress(plugin, "FH2PluginDatabaseUpdate");
    printf("exports: init %d, database %d\n", init != NULL, update != NULL);
    if (!init || !update) return 2;
    FH2PluginContext c = {0};
    c.size = sizeof c;
    c.api_version = FH2_PLUGIN_API_VERSION;
    c.log_utf8 = log_line;
    init(&c);
    void *db = NULL;
    if (open(argv[2], &db)) return 3;
    exec(db, "BEGIN", NULL, NULL, NULL);
    FH2PluginDatabaseFrame f = {0};
    f.size = sizeof f;
    f.api_version = FH2_PLUGIN_API_VERSION;
    f.database = db;
    f.prepare = (void *)GetProcAddress(sql, "sqlite3_prepare_v2");
    f.step = (void *)GetProcAddress(sql, "sqlite3_step");
    f.finalize = (void *)GetProcAddress(sql, "sqlite3_finalize");
    f.column_int64 = (void *)GetProcAddress(sql, "sqlite3_column_int64");
    printf("first call: %d\n", update(&f));
    printf("second call (must add nothing): %d\n", update(&f));
    exec(db, "COMMIT", NULL, NULL, NULL);
    close_db(db);
    return 0;
}
