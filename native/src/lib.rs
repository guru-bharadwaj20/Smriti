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

/// Vectors held once on the Rust side so graph construction compares stored
/// nodes by slot without converting Python tuples on every call.
#[pyclass]
struct VectorStore {
    vectors: Vec<Vec<f64>>,
}

#[pymethods]
impl VectorStore {
    #[new]
    fn new() -> Self {
        VectorStore { vectors: Vec::new() }
    }

    fn push(&mut self, vector: Vec<f64>) -> usize {
        self.vectors.push(vector);
        self.vectors.len() - 1
    }

    /// Same left-to-right f64 accumulation as `distance`.
    fn distance(&self, left: usize, right: usize) -> PyResult<f64> {
        let (Some(a), Some(b)) = (self.vectors.get(left), self.vectors.get(right)) else {
            return Err(PyValueError::new_err("unknown vector slot"));
        };
        if a.len() != b.len() {
            return Err(PyValueError::new_err("dimension mismatch"));
        }
        let mut dot = 0.0_f64;
        for (x, y) in a.iter().zip(b.iter()) {
            dot += x * y;
        }
        Ok((1.0 - dot).clamp(0.0, 2.0))
    }
}

#[pymodule]
fn smriti_native(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(distance, module)?)?;
    module.add_class::<VectorStore>()?;
    Ok(())
}
