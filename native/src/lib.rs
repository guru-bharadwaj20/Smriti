use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

/// Normalized-vector distance with the same left-to-right f64 accumulation as Python.
#[pyfunction]
fn distance(left: Vec<f64>, right: Vec<f64>) -> PyResult<f64> {
    if left.len() != right.len() {
        return Err(PyValueError::new_err("dimension mismatch"));
    }
    let mut dot = 0.0_f64;
    for (a, b) in left.iter().zip(right.iter()) {
        dot += a * b;
    }
    Ok((1.0 - dot).clamp(0.0, 2.0))
}

#[pymodule]
fn smriti_native(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(distance, module)?)?;
    Ok(())
}
