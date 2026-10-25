package ui

import (
	"os"
	"syscall"
	"unsafe"
)

// isTerminal reports whether "f" is an interactive terminal (TTY), without
// external dependencies.
//
// Checking ModeCharDevice is not enough: /dev/null is a character device
// too, so `pip install x < /dev/null` (common in CI) would be mistaken for an
// interactive session. The get-termios ioctl succeeds only on terminals.
func isTerminal(f *os.File) bool {
	var t syscall.Termios
	_, _, errno := syscall.Syscall(syscall.SYS_IOCTL, f.Fd(), uintptr(ioctlGetTermios), uintptr(unsafe.Pointer(&t)))
	return errno == 0
}
