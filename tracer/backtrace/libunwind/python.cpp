#include <Python.h>
#include "backtrace.h"

PyObject* module_get_backtrace(PyObject *self, PyObject *args);
PyObject* module_destroy(PyObject *self, PyObject *args);
PyObject* module_init(PyObject *self, PyObject *args);

PyObject* exceptionObj;
PyMethodDef methods[] = {
    {"init", module_init, METH_VARARGS, "initialize module, call only once"},
    {"destroy", module_destroy, METH_VARARGS, "destroy pid if provided in argument, otherwise destroy all pids and initialized module"},
    {"get_backtrace", module_get_backtrace, METH_VARARGS, "get list of backtrace frames for process"},
    {NULL, NULL, 0, NULL}
};
struct PyModuleDef module = {PyModuleDef_HEAD_INIT, "tracer.backtrace.libunwind", NULL, -1, methods};

PyMODINIT_FUNC PyInit_libunwind() {
    PyObject *m;
    m = PyModule_Create(&module);
    if (m == NULL)
        return nullptr;

    exceptionObj = PyErr_NewException("libunwind.error", NULL, NULL);
    Py_INCREF(exceptionObj);

    PyModule_AddObject(m, "error", exceptionObj);
    return m;
}

PyObject* module_init(PyObject *self, PyObject *args) {
    try {
        init();
    } catch(BacktraceException& e) {
        PyErr_SetString(exceptionObj, e.what());
        return nullptr;
    }

    return Py_BuildValue("");
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
    try {
        auto addrs = get_backtrace(pid);
        for(auto addr: addrs) {
            PyList_Append(res, Py_BuildValue("l", addr));
        }
        return res;
    } catch(BacktraceException& e) {
        PyErr_SetString(exceptionObj, e.what());
        return nullptr;
    }
}