use pyo3::prelude::*;
use std::collections::HashMap;
use std::mem;
use std::os::unix::io::RawFd;

const ACTION_NONE: u8 = 0;
const ACTION_PASSTHROUGH: u8 = 1;
const ACTION_KEYSTROKE: u8 = 2;
const ACTION_SCROLL_UP: u8 = 3;
const ACTION_SCROLL_DOWN: u8 = 4;
const ACTION_BTN_X1: u8 = 5;
const ACTION_BTN_X2: u8 = 6;

const EV_SYN: u16 = 0x00;
const EV_KEY: u16 = 0x01;
const EV_REL: u16 = 0x02;
const SYN_REPORT: u16 = 0x00;
const REL_WHEEL: u16 = 0x08;
const BTN_SIDE: u16 = 0x113;
const BTN_EXTRA: u16 = 0x114;

#[repr(C)]
#[derive(Debug, Clone, Copy)]
struct InputEvent {
    time: libc::timeval,
    type_: u16,
    code: u16,
    value: i32,
}

impl Default for InputEvent {
    fn default() -> Self {
        unsafe { mem::zeroed() }
    }
}

#[derive(Clone, Copy)]
struct MappingEntry {
    action_type: u8,
    target_code: u16,
}

#[inline(always)]
fn emit_event(fd: RawFd, type_: u16, code: u16, value: i32) {
    let mut ev = InputEvent::default();
    ev.type_ = type_;
    ev.code = code;
    ev.value = value;
    unsafe {
        libc::write(
            fd,
            &ev as *const _ as *const libc::c_void,
            mem::size_of::<InputEvent>(),
        );
    }
}

#[inline(always)]
fn emit_syn(fd: RawFd) {
    emit_event(fd, EV_SYN, SYN_REPORT, 0);
}

#[pyfunction]
fn run_remap_loop(
    py: Python,
    input_fd: RawFd,
    uinput_fd: RawFd,
    mappings: HashMap<u16, (u8, u16)>,
) -> PyResult<()> {
    let max_code = mappings.keys().max().copied().unwrap_or(0) as usize;
    let mut fast_map =
        vec![MappingEntry { action_type: ACTION_PASSTHROUGH, target_code: 0 }; max_code + 1];

    for (code, (action, target)) in mappings {
        fast_map[code as usize] = MappingEntry {
            action_type: action,
            target_code: target,
        };
    }

    py.allow_threads(|| {
        let mut ev = InputEvent::default();
        let size = mem::size_of::<InputEvent>();

        loop {
            let ret = unsafe { libc::read(input_fd, &mut ev as *mut _ as *mut libc::c_void, size) };
            if ret <= 0 {
                break;
            }

            if ev.type_ == EV_KEY {
                let code = ev.code as usize;
                if code >= fast_map.len() {
                    unsafe {
                        libc::write(uinput_fd, &ev as *const _ as *const libc::c_void, size);
                    }
                    continue;
                }

                let mapping = fast_map[code];
                match mapping.action_type {
                    ACTION_NONE => {}
                    ACTION_PASSTHROUGH => unsafe {
                        libc::write(uinput_fd, &ev as *const _ as *const libc::c_void, size);
                    },
                    ACTION_KEYSTROKE => {
                        emit_event(uinput_fd, EV_KEY, mapping.target_code, ev.value);
                        emit_syn(uinput_fd);
                    }
                    ACTION_SCROLL_UP => {
                        if ev.value == 1 {
                            emit_event(uinput_fd, EV_REL, REL_WHEEL, 1);
                            emit_syn(uinput_fd);
                        }
                    }
                    ACTION_SCROLL_DOWN => {
                        if ev.value == 1 {
                            emit_event(uinput_fd, EV_REL, REL_WHEEL, -1);
                            emit_syn(uinput_fd);
                        }
                    }
                    ACTION_BTN_X1 => {
                        if ev.value == 1 {
                            emit_event(uinput_fd, EV_KEY, BTN_SIDE, 1);
                            emit_event(uinput_fd, EV_KEY, BTN_SIDE, 0);
                            emit_syn(uinput_fd);
                        }
                    }
                    ACTION_BTN_X2 => {
                        if ev.value == 1 {
                            emit_event(uinput_fd, EV_KEY, BTN_EXTRA, 1);
                            emit_event(uinput_fd, EV_KEY, BTN_EXTRA, 0);
                            emit_syn(uinput_fd);
                        }
                    }
                    _ => unsafe {
                        libc::write(uinput_fd, &ev as *const _ as *const libc::c_void, size);
                    },
                }
            } else {
                unsafe {
                    libc::write(uinput_fd, &ev as *const _ as *const libc::c_void, size);
                }
            }
        }
    });

    Ok(())
}

#[pymodule]
fn synapse_native(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(run_remap_loop, m)?)?;
    Ok(())
}
