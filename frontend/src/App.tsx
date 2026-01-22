import { useCallback, useEffect, useState } from "react";
import { X } from "lucide-react";
import { FilePond } from "react-filepond";
import { useLocalStorage } from "react-use";
import { AnimatePresence, motion } from "motion/react";
import { cubicBezier } from "motion";
import { Button } from "./components/ui/button";
import { Tabs, TabsContent, TabsContents } from "./components/animate-ui/components/animate/tabs";
import { FilePondErrorDescription, FilePondFile } from "filepond";

const toBase64 = (file: File) => new Promise((resolve, reject) => {
  const reader = new FileReader();
  reader.readAsDataURL(file);
  reader.onload = () => {
    resolve(reader.result); // reader.result looks like: "data:application/pdf;base64,JVBER..."
  };
  reader.onerror = error => reject(error);
});

export default function App() {
  // Pywebview interface
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

  // Log pywebview object when it changes
  useEffect(() => {
    console.log("Pywebview object:", pywebview);
  }, [pywebview]);

  // Status from pywebview
  const [status, setStatus] = useState<string | null>(null);

  // Fist use flag
  const [firstUse, setFirstUse] = useLocalStorage("stemu-first-use", true);

  // Step
  const [step, setStep] = useState("file-select");

  // Selected files
  // TODO: SOMEHOW MAKE EVERYTHING HAVE THE SAME ORDER
  const maxFiles = 5;
  const [fileCount, setFileCount] = useState<number>(0);
  const [files, setFiles] = useState<FilePondFile[]>([]);
  const [fileProcessingResults, setFileProcessingResults] = useState<{filename: string, file_path: string, waveform_path: string}[]>([]);

  useEffect(() => {
    console.log("Files: ", files);
    console.log("Processing results: ", fileProcessingResults);
  }, [files, fileProcessingResults]);

  // TODO: Consider using useReducer
  const addFile = useCallback((_err: FilePondErrorDescription | null, file: FilePondFile, cnt) => {
    console.log("File count", cnt);
    if (cnt + 1 > maxFiles) return;

    setFiles(prev => Array.from(new Set([...prev, file])));
    setFileCount(prev => prev + 1);

    console.log("Adding file:", file);
    console.log("Pywebview ready:", !!pywebview);

    setStatus(`Processing files...`);
    console.log("Sending file to Python:", file.filename, file.id);
    toBase64(file.file as File).then(data => {
      window.pywebview.api.addFile<{filename: string, file_path: string, waveform_path: string}>({
        filename: file.filename,
        id: file.id,
        data
      }).then(res => {
        setFileProcessingResults(prev => [...prev, res]);
        setStatus(`File processed successfully.`);
        console.log("File processed successfully");
        return res;
      }).then(console.log);
    }).then(() => {
      console.log("File sent to Python successfully.");
      
    });
  }, [pywebview]);

  const removeFile = (_err: FilePondErrorDescription | null, file: FilePondFile) => {
    setFiles(prev => prev.filter(f => f.file !== file.file));
    console.log("Removing file:", file.filename);
    setFileProcessingResults(prev => prev.filter(f => f.filename !== file.filename));
    console.log(fileProcessingResults);
  }

  return (
    <div className="w-screen h-screen relative flex flex-col overflow-hidden border border-[#ffffff33]">
      {/* Title bar */}
      <div className="pywebview-drag-region bg-[#0d0d0d] text-white w-full h-8 flex items-center justify-between z-[9999999] relative">
          <div className="flex px-2 gap-4 items-center overflow-clip">
              <p className='font-bold'>STEMu</p>
              <span className="opacity-75 h-full">
                <AnimatePresence mode="wait">
                  <motion.p 
                    key={status}
                    className='text-sm leading-0 mt-1'
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    transition={{ duration: 0.3 }}
                  >{status}</motion.p>
                </AnimatePresence>
              </span>
          </div>
          <button className='aspect-square h-full cursor-pointer hover:*:scale-125' onClick={() => window.pywebview.api.close()}>
              <X color="#fff"></X>
          </button>
      </div>

      {/* Welcome screen */}
      <AnimatePresence>
        {firstUse ? <>
          <motion.div 
            className={`w-full h-full flex flex-col justify-center gap-2 pb-16 bg-[#121212] z-10 absolute`}
            exit={{ y: "-100%" }}
            transition={{ duration: 0.5, ease: cubicBezier(0.65, 0, 0.35, 1) }}
          >
            <motion.h1
              className="w-full text-center text-3xl font-bold"
              initial={{ scale: 0.5, opacity: 0, y: 50 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              transition={{ delay: 0.25, duration: 1, ease: cubicBezier(0.65, 0, 0.35, 1) }}
            >Welcome to STEMu</motion.h1>

            <motion.p
              className="w-full text-center"
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.75 }}
              transition={{ delay: 1, duration: 1 }}
            >Effortless STEM separation</motion.p>

            <motion.div
              className="w-full flex justify-center absolute bottom-20"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 1, duration: 1 }}
            >
              <Button onClick={() => setFirstUse(false)}>Continue</Button>
            </motion.div>
          </motion.div>
        </> : null}
      </AnimatePresence>

      {/* Step screens */}
      <Tabs value={step} className="w-full h-full">
        <TabsContents className="w-full h-full! relative">
          {/* File Select */}
          <TabsContent value="file-select" className="w-full h-full">
            <div className="w-full h-full flex items-center justify-center">
              <div className="w-full p-6 h-full">
                <p className="-mt-2 text-sm opacity-50">Max. 5 Files</p>
                {/* TODO: Allow multiple files */}
                <FilePond 
                  key="file-select"
                  allowMultiple
                  files={files.map(f => f.file)}
                  onaddfile={(err, file) => addFile(err, file, fileCount)}
                  onremovefile={removeFile}
                  dropOnPage={true}
                  acceptedFileTypes={["wav", "mp3", "flac", "m4a", "ogg"]}
                  labelIdle='Drop your file here or <span class="filepond--label-action"> Browse </span> to get started'
                ></FilePond>
              </div>
            </div>

            <div className="w-full flex justify-end p-6 absolute bottom-0 right-0">
              <Button disabled={files.length === 0} onClick={() => setStep("settings")}>Next</Button>
            </div>
          </TabsContent>

          {/* Settings */}
          <TabsContent value="settings" className="w-full h-full relative">
            <div className="w-full flex justify-between p-6 absolute bottom-0 right-0">
              <Button onClick={() => setStep("file-select")} variant="outline">Back</Button>
              <Button onClick={() => setStep("separate")}>Next</Button>
            </div>
          </TabsContent>


        </TabsContents>
      </Tabs>
    </div>
  )
}