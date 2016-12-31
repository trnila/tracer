#include <Python.h>

extern "C" {
    void init();
    long* get_backtrace(int pid);
    void destroy_pid(int pid);
    void destroy();
}

PyObject* module_destroy(PyObject *self, PyObject *args) {
    if(PyTuple_Size(args) == 0) {
        destroy();
    } else {
        int pid;
        if(!PyArg_ParseTuple(args, "i", &pid)) {
            pid = 0;
        }

        if(pid == 0) {
            destroy();
        } else {
            destroy_pid(pid);
        }
    }
    return Py_BuildValue("");
}


PyObject* module_get_backtrace(PyObject *self, PyObject *args) {
    int pid;
    if(!PyArg_ParseTuple(args, "i", &pid)) {
        return NULL;
    }

    PyObject* res = Py_BuildValue("[]");
    long *addrs = get_backtrace(pid);
    while(*addrs != 0) {
        PyList_Append(res, Py_BuildValue("l", *addrs));
        addrs++;
    }

    return res;
}

PyMethodDef methods[] = {
    {"destroy", module_destroy, METH_VARARGS, "Execute a shell command."},
    {"get_backtrace", module_get_backtrace, METH_VARARGS, "Execute a shell command."},
    {NULL, NULL, 0, NULL}
};

struct PyModuleDef module = {PyModuleDef_HEAD_INIT, "backtrace", NULL, -1, methods};

PyMODINIT_FUNC PyInit_backtrace() {
    init();
    return PyModule_Create(&module);
}
