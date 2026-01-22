import { useState, useEffect } from 'react';

const usePywebview = () => {
    const [pywebview, setPywebview] = useState<any>(window.pywebview);
    useEffect(() =>{
      if (!window.pywebview) {
        const handleReady = () => setPywebview(window.pywebview);
        window.addEventListener('pywebviewready', handleReady);
        return () => window.removeEventListener('pywebviewready', handleReady);
      } else {
        setPywebview(window.pywebview);
      }
    }, []);

  /**
   * Safe wrapper to call Python functions.
   * @param {string} funcName - The name of the function in your Python API class.
   * @param {...args} args - Arguments to pass to the Python function.
   */
  const callPython = async (funcName, ...args) => {
    if (!pywebview) {
      console.warn("Pywebview is not initialized yet.");
      return null;
    }

    const apiFunc = window.pywebview.api[funcName];
    if (typeof apiFunc !== 'function') {
      console.error(`Function "${funcName}" not found in Python API.`);
      return null;
    }

    try {
      return await apiFunc(...args);
    } catch (error) {
      console.error(`Error calling Python function "${funcName}":`, error);
      throw error;
    }
  };

  return { isReady: !!pywebview, callPython, pywebview, api: window.pywebview?.api };
};

export default usePywebview;