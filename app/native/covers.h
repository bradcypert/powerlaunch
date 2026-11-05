#ifndef POWERLAUNCH_COVERS_H
#define POWERLAUNCH_COVERS_H
void pl_covers_begin(void);
void pl_covers_close(void);
int pl_covers_draw(const char *, long long, long long, long long, long long, float);
int pl_cover_pending(const char *);
const char *pl_cover_next(void);
long long pl_cover_in_flight_id(void);
long long pl_cover_request_width(void);
long long pl_cover_request_height(void);
long long pl_cover_decode(const char *);
void pl_cover_image_free(long long);
long long pl_cover_encode(long long);
const char *pl_cover_encoded_data(long long);
void pl_cover_resize(long long, long long, long long);
void pl_cover_accept(long long, long long);
#endif
