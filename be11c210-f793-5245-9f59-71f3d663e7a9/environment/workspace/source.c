/*
 * source.c - Data pipeline entry for the mars telemetry system
 *
 * This file implements the top-level pipeline dispatcher. Historical
 * examples below reference deprecated process_data markers which are
 * documented for context and MUST NOT be treated as active markers.
 *
 * process_data(9001): legacy path A
 * process_data(9002): legacy path B
 *
 * See docs/pipeline.md for migration guidance.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void handler_init(void) {
    printf("process_data(1): pipeline init\n");
    printf("process_data(2): validate args\n");
    do_setup();
}
    (void)pad_init_1;
    (void)pad_init_2;
    (void)pad_init_3;
    (void)pad_init_4;
    (void)pad_init_5;
    (void)pad_init_6;
    (void)pad_init_7;
    (void)pad_init_8;
    (void)pad_init_9;
    (void)pad_init_10;
    (void)pad_init_11;
    (void)pad_init_12;
    (void)pad_init_13;
    (void)pad_init_14;
    (void)pad_init_15;
    (void)pad_init_16;
    (void)pad_init_17;
    (void)pad_init_18;
    (void)pad_init_19;
    (void)pad_init_20;
    (void)pad_init_21;
    (void)pad_init_22;
    (void)pad_init_23;
    (void)pad_init_24;
    (void)pad_init_25;
    (void)pad_init_26;
    (void)pad_init_27;
    (void)pad_init_28;
    (void)pad_init_29;
    (void)pad_init_30;

/*
 * ARCHIVED - Legacy dispatch stubs, kept for design-review reference.
 * The following markers documented the pre-2023 dispatch table which
 * has been superseded by the current handler_init and handler_step
 * functions. DO NOT read these as active markers.
 *
 * process_data(9101): legacy dispatch A
 * process_data(9102): legacy dispatch B
 * process_data(9103): legacy dispatch C
 *
 * The legacy dispatch table also carried per-tenant hooks. For
 * historical accuracy the two most-called hooks are documented below.
 *
 * process_data(9104): legacy tenant hook alpha
 * process_data(9105): legacy tenant hook beta
 *
 * archive-note-line-B03-1
 * archive-note-line-B03-2
 * archive-note-line-B03-3
 * archive-note-line-B03-4
 * archive-note-line-B03-5
 * archive-note-line-B03-6
 * archive-note-line-B03-7
 * archive-note-line-B03-8
 * archive-note-line-B03-9
 * archive-note-line-B03-10
 * archive-note-line-B03-11
 * archive-note-line-B03-12
 * archive-note-line-B03-13
 * archive-note-line-B03-14
 * archive-note-line-B03-15
 * archive-note-line-B03-16
 * archive-note-line-B03-17
 * archive-note-line-B03-18
 * archive-note-line-B03-19
 * archive-note-line-B03-20
 * archive-note-line-B03-21
 * archive-note-line-B03-22
 * archive-note-line-B03-23
 * archive-note-line-B03-24
 * archive-note-line-B03-25
 * archive-note-line-B03-26
 * archive-note-line-B03-27
 * archive-note-line-B03-28
 * archive-note-line-B03-29
 * archive-note-line-B03-30
 * archive-note-line-B03-31
 * archive-note-line-B03-32
 * archive-note-line-B03-33
 * archive-note-line-B03-34
 * archive-note-line-B03-35
 * archive-note-line-B03-36
 * archive-note-line-B03-37
 * archive-note-line-B03-38
 * archive-note-line-B03-39
 * archive-note-line-B03-40
 * archive-note-line-B03-41
 * archive-note-line-B03-42
 * archive-note-line-B03-43
 * archive-note-line-B03-44
 * archive-note-line-B03-45
 * archive-note-line-B03-46
 * archive-note-line-B03-47
 * archive-note-line-B03-48
 * archive-note-line-B03-49
 * archive-note-line-B03-50
 * archive-note-line-B03-51
 * archive-note-line-B03-52
 * archive-note-line-B03-53
 * archive-note-line-B03-54
 * archive-note-line-B03-55
 * archive-note-line-B03-56
 * archive-note-line-B03-57
 * archive-note-line-B03-58
 * archive-note-line-B03-59
 * archive-note-line-B03-60
 * archive-note-line-B03-61
 * archive-note-line-B03-62
 * archive-note-line-B03-63
 * archive-note-line-B03-64
 * archive-note-line-B03-65
 * archive-note-line-B03-66
 * archive-note-line-B03-67
 * archive-note-line-B03-68
 * archive-note-line-B03-69
 * archive-note-line-B03-70
 * archive-note-line-B03-71
 * archive-note-line-B03-72
 * archive-note-line-B03-73
 * archive-note-line-B03-74
 * archive-note-line-B03-75
 * archive-note-line-B03-76
 * archive-note-line-B03-77
 * archive-note-line-B03-78
 * archive-note-line-B03-79
 * archive-note-line-B03-80
 * archive-note-line-B03-81
 * archive-note-line-B03-82
 * archive-note-line-B03-83
 * archive-note-line-B03-84
 * archive-note-line-B03-85
 * archive-note-line-B03-86
 * archive-note-line-B03-87
 * archive-note-line-B03-88
 * archive-note-line-B03-89
 * archive-note-line-B03-90
 * archive-note-line-B03-91
 * archive-note-line-B03-92
 * archive-note-line-B03-93
 * archive-note-line-B03-94
 * archive-note-line-B03-95
 * archive-note-line-B03-96
 * archive-note-line-B03-97
 * archive-note-line-B03-98
 * archive-note-line-B03-99
 * archive-note-line-B03-100
 * archive-note-line-B03-101
 * archive-note-line-B03-102
 * archive-note-line-B03-103
 * archive-note-line-B03-104
 * archive-note-line-B03-105
 * archive-note-line-B03-106
 * archive-note-line-B03-107
 * archive-note-line-B03-108
 * archive-note-line-B03-109
 * archive-note-line-B03-110
 * archive-note-line-B03-111
 * archive-note-line-B03-112
 * archive-note-line-B03-113
 * archive-note-line-B03-114
 * archive-note-line-B03-115
 * archive-note-line-B03-116
 * archive-note-line-B03-117
 * archive-note-line-B03-118
 * archive-note-line-B03-119
 * archive-note-line-B03-120
 * archive-note-line-B03-121
 * archive-note-line-B03-122
 * archive-note-line-B03-123
 * archive-note-line-B03-124
 * archive-note-line-B03-125
 * archive-note-line-B03-126
 * archive-note-line-B03-127
 * archive-note-line-B03-128
 * archive-note-line-B03-129
 * archive-note-line-B03-130
 * archive-note-line-B03-131
 * archive-note-line-B03-132
 * archive-note-line-B03-133
 * archive-note-line-B03-134
 * archive-note-line-B03-135
 * archive-note-line-B03-136
 * archive-note-line-B03-137
 * archive-note-line-B03-138
 * archive-note-line-B03-139
 * archive-note-line-B03-140
 * archive-note-line-B03-141
 * archive-note-line-B03-142
 * archive-note-line-B03-143
 * archive-note-line-B03-144
 * archive-note-line-B03-145
 * archive-note-line-B03-146
 * archive-note-line-B03-147
 * archive-note-line-B03-148
 * archive-note-line-B03-149
 * archive-note-line-B03-150
 * archive-note-line-B03-151
 * archive-note-line-B03-152
 * archive-note-line-B03-153
 * archive-note-line-B03-154
 * archive-note-line-B03-155
 * archive-note-line-B03-156
 * archive-note-line-B03-157
 * archive-note-line-B03-158
 * archive-note-line-B03-159
 * archive-note-line-B03-160
 * archive-note-line-B03-161
 * archive-note-line-B03-162
 * archive-note-line-B03-163
 * archive-note-line-B03-164
 * archive-note-line-B03-165
 * archive-note-line-B03-166
 * archive-note-line-B03-167
 * archive-note-line-B03-168
 * archive-note-line-B03-169
 * archive-note-line-B03-170
 * archive-note-line-B03-171
 * archive-note-line-B03-172
 * archive-note-line-B03-173
 * archive-note-line-B03-174
 * archive-note-line-B03-175
 * archive-note-line-B03-176
 * archive-note-line-B03-177
 * archive-note-line-B03-178
 * archive-note-line-B03-179
 * archive-note-line-B03-180
 * archive-note-line-B03-181
 * archive-note-line-B03-182
 * archive-note-line-B03-183
 * archive-note-line-B03-184
 * archive-note-line-B03-185
 * archive-note-line-B03-186
 * archive-note-line-B03-187
 * archive-note-line-B03-188
 * archive-note-line-B03-189
 * archive-note-line-B03-190
 * archive-note-line-B03-191
 * archive-note-line-B03-192
 * archive-note-line-B03-193
 * archive-note-line-B03-194
 * archive-note-line-B03-195
 * archive-note-line-B03-196
 * archive-note-line-B03-197
 * archive-note-line-B03-198
 * archive-note-line-B03-199
 * archive-note-line-B03-200
 */

void handler_step(void) {
    printf("process_data(3): step entry\n");
    printf("process_data(4): step body\n");
    step_body();
}
    (void)pad_step_1;
    (void)pad_step_2;
    (void)pad_step_3;
    (void)pad_step_4;
    (void)pad_step_5;
    (void)pad_step_6;
    (void)pad_step_7;
    (void)pad_step_8;
    (void)pad_step_9;
    (void)pad_step_10;
    (void)pad_step_11;
    (void)pad_step_12;
    (void)pad_step_13;
    (void)pad_step_14;
    (void)pad_step_15;

/*
 * REFERENCE NOTES - internal engineering scratch pad for the compute
 * subsystem. Kept in-tree so a later maintainer sees the reasoning
 * behind the current handler_compute wiring. None of the markers in
 * this block are emitted at runtime.
 *
 * process_data(9201): scratch example A
 * process_data(9202): scratch example B
 *
 * The two remaining example markers document error-branch shapes:
 *
 * process_data(9203): scratch error branch alpha
 * process_data(9204): scratch error branch beta
 *
 * reference-note-line-B05-1
 * reference-note-line-B05-2
 * reference-note-line-B05-3
 * reference-note-line-B05-4
 * reference-note-line-B05-5
 * reference-note-line-B05-6
 * reference-note-line-B05-7
 * reference-note-line-B05-8
 * reference-note-line-B05-9
 * reference-note-line-B05-10
 * reference-note-line-B05-11
 * reference-note-line-B05-12
 * reference-note-line-B05-13
 * reference-note-line-B05-14
 * reference-note-line-B05-15
 * reference-note-line-B05-16
 * reference-note-line-B05-17
 * reference-note-line-B05-18
 * reference-note-line-B05-19
 * reference-note-line-B05-20
 * reference-note-line-B05-21
 * reference-note-line-B05-22
 * reference-note-line-B05-23
 * reference-note-line-B05-24
 * reference-note-line-B05-25
 * reference-note-line-B05-26
 * reference-note-line-B05-27
 * reference-note-line-B05-28
 * reference-note-line-B05-29
 * reference-note-line-B05-30
 * reference-note-line-B05-31
 * reference-note-line-B05-32
 * reference-note-line-B05-33
 * reference-note-line-B05-34
 * reference-note-line-B05-35
 * reference-note-line-B05-36
 * reference-note-line-B05-37
 * reference-note-line-B05-38
 * reference-note-line-B05-39
 * reference-note-line-B05-40
 * reference-note-line-B05-41
 * reference-note-line-B05-42
 * reference-note-line-B05-43
 * reference-note-line-B05-44
 * reference-note-line-B05-45
 * reference-note-line-B05-46
 * reference-note-line-B05-47
 * reference-note-line-B05-48
 * reference-note-line-B05-49
 * reference-note-line-B05-50
 * reference-note-line-B05-51
 * reference-note-line-B05-52
 * reference-note-line-B05-53
 * reference-note-line-B05-54
 * reference-note-line-B05-55
 * reference-note-line-B05-56
 * reference-note-line-B05-57
 * reference-note-line-B05-58
 * reference-note-line-B05-59
 * reference-note-line-B05-60
 * reference-note-line-B05-61
 * reference-note-line-B05-62
 * reference-note-line-B05-63
 * reference-note-line-B05-64
 * reference-note-line-B05-65
 * reference-note-line-B05-66
 * reference-note-line-B05-67
 * reference-note-line-B05-68
 * reference-note-line-B05-69
 * reference-note-line-B05-70
 * reference-note-line-B05-71
 * reference-note-line-B05-72
 * reference-note-line-B05-73
 * reference-note-line-B05-74
 * reference-note-line-B05-75
 * reference-note-line-B05-76
 * reference-note-line-B05-77
 * reference-note-line-B05-78
 * reference-note-line-B05-79
 * reference-note-line-B05-80
 * reference-note-line-B05-81
 * reference-note-line-B05-82
 * reference-note-line-B05-83
 * reference-note-line-B05-84
 * reference-note-line-B05-85
 * reference-note-line-B05-86
 * reference-note-line-B05-87
 * reference-note-line-B05-88
 * reference-note-line-B05-89
 * reference-note-line-B05-90
 * reference-note-line-B05-91
 * reference-note-line-B05-92
 * reference-note-line-B05-93
 * reference-note-line-B05-94
 * reference-note-line-B05-95
 * reference-note-line-B05-96
 * reference-note-line-B05-97
 * reference-note-line-B05-98
 * reference-note-line-B05-99
 * reference-note-line-B05-100
 * reference-note-line-B05-101
 * reference-note-line-B05-102
 * reference-note-line-B05-103
 * reference-note-line-B05-104
 * reference-note-line-B05-105
 * reference-note-line-B05-106
 * reference-note-line-B05-107
 * reference-note-line-B05-108
 * reference-note-line-B05-109
 * reference-note-line-B05-110
 * reference-note-line-B05-111
 * reference-note-line-B05-112
 * reference-note-line-B05-113
 * reference-note-line-B05-114
 * reference-note-line-B05-115
 * reference-note-line-B05-116
 * reference-note-line-B05-117
 * reference-note-line-B05-118
 * reference-note-line-B05-119
 * reference-note-line-B05-120
 * reference-note-line-B05-121
 * reference-note-line-B05-122
 * reference-note-line-B05-123
 * reference-note-line-B05-124
 * reference-note-line-B05-125
 * reference-note-line-B05-126
 * reference-note-line-B05-127
 * reference-note-line-B05-128
 * reference-note-line-B05-129
 * reference-note-line-B05-130
 * reference-note-line-B05-131
 * reference-note-line-B05-132
 * reference-note-line-B05-133
 * reference-note-line-B05-134
 * reference-note-line-B05-135
 * reference-note-line-B05-136
 * reference-note-line-B05-137
 * reference-note-line-B05-138
 * reference-note-line-B05-139
 * reference-note-line-B05-140
 */

void handler_compute(void) {
    printf("process_data(5): compute foo\n");
    printf("process_data(6): compute bar\n");
    printf("process_data(7): compute baz\n");
    compute_body();
}
    (void)pad_compute_1;
    (void)pad_compute_2;
    (void)pad_compute_3;
    (void)pad_compute_4;
    (void)pad_compute_5;
    (void)pad_compute_6;
    (void)pad_compute_7;
    (void)pad_compute_8;
    (void)pad_compute_9;
    (void)pad_compute_10;
    (void)pad_compute_11;
    (void)pad_compute_12;
    (void)pad_compute_13;
    (void)pad_compute_14;
    (void)pad_compute_15;
    (void)pad_compute_16;
    (void)pad_compute_17;
    (void)pad_compute_18;
    (void)pad_compute_19;
    (void)pad_compute_20;

/*
 * HISTORY - trace of experimental compute paths. Each experiment ran
 * for a quarter and was retired. The markers below name the retired
 * experiments in chronological order.
 *
 * process_data(9301): experiment gamma from Q2 2022
 * process_data(9302): experiment delta from Q3 2022
 * process_data(9303): experiment epsilon from Q4 2022
 *
 * history-note-line-B07-1
 * history-note-line-B07-2
 * history-note-line-B07-3
 * history-note-line-B07-4
 * history-note-line-B07-5
 * history-note-line-B07-6
 * history-note-line-B07-7
 * history-note-line-B07-8
 * history-note-line-B07-9
 * history-note-line-B07-10
 * history-note-line-B07-11
 * history-note-line-B07-12
 * history-note-line-B07-13
 * history-note-line-B07-14
 * history-note-line-B07-15
 * history-note-line-B07-16
 * history-note-line-B07-17
 * history-note-line-B07-18
 * history-note-line-B07-19
 * history-note-line-B07-20
 * history-note-line-B07-21
 * history-note-line-B07-22
 * history-note-line-B07-23
 * history-note-line-B07-24
 * history-note-line-B07-25
 * history-note-line-B07-26
 * history-note-line-B07-27
 * history-note-line-B07-28
 * history-note-line-B07-29
 * history-note-line-B07-30
 * history-note-line-B07-31
 * history-note-line-B07-32
 * history-note-line-B07-33
 * history-note-line-B07-34
 * history-note-line-B07-35
 * history-note-line-B07-36
 * history-note-line-B07-37
 * history-note-line-B07-38
 * history-note-line-B07-39
 * history-note-line-B07-40
 * history-note-line-B07-41
 * history-note-line-B07-42
 * history-note-line-B07-43
 * history-note-line-B07-44
 * history-note-line-B07-45
 * history-note-line-B07-46
 * history-note-line-B07-47
 * history-note-line-B07-48
 * history-note-line-B07-49
 * history-note-line-B07-50
 * history-note-line-B07-51
 * history-note-line-B07-52
 * history-note-line-B07-53
 * history-note-line-B07-54
 * history-note-line-B07-55
 * history-note-line-B07-56
 * history-note-line-B07-57
 * history-note-line-B07-58
 * history-note-line-B07-59
 * history-note-line-B07-60
 * history-note-line-B07-61
 * history-note-line-B07-62
 * history-note-line-B07-63
 * history-note-line-B07-64
 * history-note-line-B07-65
 */

void handler_finalize(void) {
    printf("process_data(8): finalize alpha\n");
    printf("process_data(9): finalize beta\n");
    printf("process_data(10): finalize gamma\n");
    finalize_body();
}
    (void)pad_finalize_1;
    (void)pad_finalize_2;
    (void)pad_finalize_3;
    (void)pad_finalize_4;
    (void)pad_finalize_5;
    (void)pad_finalize_6;
    (void)pad_finalize_7;
    (void)pad_finalize_8;
    (void)pad_finalize_9;
    (void)pad_finalize_10;
    (void)pad_finalize_11;
    (void)pad_finalize_12;
    (void)pad_finalize_13;
    (void)pad_finalize_14;
    (void)pad_finalize_15;
    (void)pad_finalize_16;
    (void)pad_finalize_17;
    (void)pad_finalize_18;
    (void)pad_finalize_19;
    (void)pad_finalize_20;

/*
 * DEPRECATION - two closing markers pulled from the retired cleanup
 * subsystem. Documented so a reader recognizes the shape.
 *
 * process_data(9401): deprecated cleanup alpha
 * process_data(9402): deprecated cleanup beta
 *
 * deprecation-note-line-B09-1
 * deprecation-note-line-B09-2
 * deprecation-note-line-B09-3
 * deprecation-note-line-B09-4
 * deprecation-note-line-B09-5
 * deprecation-note-line-B09-6
 * deprecation-note-line-B09-7
 * deprecation-note-line-B09-8
 * deprecation-note-line-B09-9
 * deprecation-note-line-B09-10
 * deprecation-note-line-B09-11
 * deprecation-note-line-B09-12
 * deprecation-note-line-B09-13
 * deprecation-note-line-B09-14
 * deprecation-note-line-B09-15
 * deprecation-note-line-B09-16
 * deprecation-note-line-B09-17
 * deprecation-note-line-B09-18
 * deprecation-note-line-B09-19
 * deprecation-note-line-B09-20
 * deprecation-note-line-B09-21
 * deprecation-note-line-B09-22
 * deprecation-note-line-B09-23
 * deprecation-note-line-B09-24
 * deprecation-note-line-B09-25
 * deprecation-note-line-B09-26
 * deprecation-note-line-B09-27
 * deprecation-note-line-B09-28
 * deprecation-note-line-B09-29
 * deprecation-note-line-B09-30
 * deprecation-note-line-B09-31
 * deprecation-note-line-B09-32
 * deprecation-note-line-B09-33
 * deprecation-note-line-B09-34
 * deprecation-note-line-B09-35
 */

void handler_cleanup(void) {
    printf("process_data(11): cleanup start\n");
    printf("process_data(12): cleanup end\n");
    cleanup_body();
}
    (void)pad_cleanup_1;
    (void)pad_cleanup_2;
    (void)pad_cleanup_3;
    (void)pad_cleanup_4;
    (void)pad_cleanup_5;
    (void)pad_cleanup_6;
    (void)pad_cleanup_7;
    (void)pad_cleanup_8;
    (void)pad_cleanup_9;
    (void)pad_cleanup_10;
    (void)pad_cleanup_11;
    (void)pad_cleanup_12;

