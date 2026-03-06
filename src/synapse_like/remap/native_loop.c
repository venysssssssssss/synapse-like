/*
 * native_loop.c
 * 
 * Implementacao de alta performance do loop de remapeamento em C.
 * Projetado para ser compilado como Shared Object (.so) e usado via ctypes.
 * 
 * Compile com:
 * gcc -shared -o native_loop.so -fPIC native_loop.c
 */

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <linux/input.h>
#include <errno.h>
#include <string.h>

// Definicoes de acoes simplificadas para mapeamento direto
#define ACTION_NONE 0
#define ACTION_PASSTHROUGH 1
#define ACTION_KEYSTROKE 2
#define ACTION_SCROLL_UP 3
#define ACTION_SCROLL_DOWN 4
#define ACTION_BTN_X1 5
#define ACTION_BTN_X2 6

struct MappingEntry {
    int action_type;
    int target_code; // Para KEYSTROKE
};

// Tabela de lookup simples: codigo de entrada -> acao
// Assumindo maximo de codigos de tecla linux (~768)
#define MAX_KEY_CODES 1024
struct MappingEntry key_map[MAX_KEY_CODES];

void init_map() {
    memset(key_map, 0, sizeof(key_map));
    // Default: Passthrough para todos
    for(int i=0; i<MAX_KEY_CODES; i++) {
        key_map[i].action_type = ACTION_PASSTHROUGH;
    }
}

void set_mapping(int code, int type, int target) {
    if (code >= 0 && code < MAX_KEY_CODES) {
        key_map[code].action_type = type;
        key_map[code].target_code = target;
    }
}

void emit_event(int fd, int type, int code, int value) {
    struct input_event ev;
    memset(&ev, 0, sizeof(ev));
    ev.type = type;
    ev.code = code;
    ev.value = value;
    write(fd, &ev, sizeof(ev));
}

void emit_syn(int fd) {
    emit_event(fd, EV_SYN, SYN_REPORT, 0);
}

/*
 * Loop principal de remapeamento.
 * Retorna 0 em sucesso (parada limpa), -1 em erro.
 */
int run_remap_loop(int input_fd, int uinput_fd, int pointer_uinput_fd, volatile int* running_flag) {
    struct input_event ev;
    int rd;
    int target_fd;

    while (*running_flag) {
        rd = read(input_fd, &ev, sizeof(struct input_event));
        
        if (rd < (int)sizeof(struct input_event)) {
            if (errno == EAGAIN || errno == EWOULDBLOCK) {
                usleep(1000); // 1ms sleep se non-blocking
                continue;
            }
            // Device desconectado ou erro fatal
            return -1;
        }

        if (ev.type == EV_KEY) {
            // Verifica limites
            if (ev.code >= MAX_KEY_CODES) {
                write(uinput_fd, &ev, sizeof(ev));
                continue;
            }

            struct MappingEntry mapping = key_map[ev.code];

            switch (mapping.action_type) {
                case ACTION_NONE:
                    // Drop event
                    break;

                case ACTION_PASSTHROUGH:
                    write(uinput_fd, &ev, sizeof(ev));
                    break;

                case ACTION_KEYSTROKE:
                    emit_event(uinput_fd, EV_KEY, mapping.target_code, ev.value);
                    emit_syn(uinput_fd);
                    break;

                case ACTION_SCROLL_UP:
                    if (ev.value == 1) { // Key down only
                        target_fd = (pointer_uinput_fd > 0) ? pointer_uinput_fd : uinput_fd;
                        emit_event(target_fd, EV_REL, REL_WHEEL, 1);
                        emit_syn(target_fd);
                    }
                    break;

                case ACTION_SCROLL_DOWN:
                    if (ev.value == 1) {
                        target_fd = (pointer_uinput_fd > 0) ? pointer_uinput_fd : uinput_fd;
                        emit_event(target_fd, EV_REL, REL_WHEEL, -1);
                        emit_syn(target_fd);
                    }
                    break;
                
                case ACTION_BTN_X1:
                    if (ev.value == 1) {
                        target_fd = (pointer_uinput_fd > 0) ? pointer_uinput_fd : uinput_fd;
                        emit_event(target_fd, EV_KEY, BTN_SIDE, 1);
                        emit_event(target_fd, EV_KEY, BTN_SIDE, 0); // Click instantaneo
                        emit_syn(target_fd);
                    }
                    break;

                default:
                    // Fallback passthrough
                    write(uinput_fd, &ev, sizeof(ev));
                    break;
            }
        } else {
            // Passthrough para non-key events (mouse move, syn, msc)
            write(uinput_fd, &ev, sizeof(ev));
        }
    }
    return 0;
}