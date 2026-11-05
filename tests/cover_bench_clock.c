#include <raylib.h>
double pl_bench_time(void) { return GetTime(); }
void pl_bench_pause(void) { WaitTime(0.002); }
void pl_bench_unlimit(void) { SetTraceLogLevel(LOG_WARNING); SetTargetFPS(0); }
