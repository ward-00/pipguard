package ui

import (
	"os"
	"syscall"
	"unsafe"
)

// isTerminal uses the get-termios ioctl, which succeeds only on terminals.
// ModeCharDevice is not enough: /dev/null (common in CI) is one too.
func isTerminal(f *os.File) bool {
	var t syscall.Termios
	_, _, errno := syscall.Syscall(syscall.SYS_IOCTL, f.Fd(), uintptr(ioctlGetTermios), uintptr(unsafe.Pointer(&t)))
	return errno == 0
}
