import { useEffect, useRef, useState } from "react";
import { Pause, Play, X } from "lucide-react";
import { FilePond } from "react-filepond";
import { useHoverDirty, useLocalStorage, useMouseHovered } from "react-use";
import { AnimatePresence, motion } from "motion/react";
import { cubicBezier } from "motion";
import { Button } from "./components/ui/button";
import { Tabs, TabsContent, TabsContents } from "./components/animate-ui/components/animate/tabs";
import { FilePondErrorDescription, FilePondFile } from "filepond";
import { Select, SelectContent, SelectGroup, SelectItem, SelectLabel, SelectTrigger } from "./components/ui/select";
import { SelectValue } from "@radix-ui/react-select";
import useAudioFile from "./hooks/useAudioFile";

const waveformImages = Array(36).fill(null).map((_, i) => `/waveforms/${i}.png`);

const toBase64 = (file: File) => new Promise((resolve, reject) => {
  const reader = new FileReader();
  reader.readAsDataURL(file);
  reader.onload = () => {
    resolve(reader.result); // reader.result looks like: "data:application/pdf;base64,JVBER..."
  };
  reader.onerror = error => reject(error);
});

// TODO: backend now sends data bc wtf
type FileProcessResult = {
  filename: string,
  file_path: string,
  file_data: string,
  waveform_path: string,
  waveform_data: string,
};
const SpleeterModels = {
  "2stems": {displayName: "2 STEMs", description: "Vocals / instrumental"},
  "4stems": {displayName: "4 STEMs", description: "Vocals / drums / bass / other"},
  "5stems": {displayName: "5 STEMs", description: "Vocals / drums / bass / piano / other"}
} as const;
type SpleeterModel = keyof typeof SpleeterModels;
class FileWrapper {
  public file: FilePondFile = null;
  public processed: FileProcessResult | null = null;
  public model: SpleeterModel = "2stems";

  constructor(file: FilePondFile, processed: FileProcessResult | null = null, model: SpleeterModel = "2stems") {
    this.file = file;
    this.processed = processed;
    this.model = model;
  }
}

function FilePreview({ file }: { file: FileWrapper }) {
  const [fakeWaveformPerc, setFakeWaveformPerc] = useState(0);
  const waveformContainerRef = useRef<HTMLDivElement>(null);

  const { elX } = useMouseHovered(waveformContainerRef, { bound: true, whenHovered: true });
  const waveformHovered = useHoverDirty(waveformContainerRef);

  useEffect(() => {
    console.log("Mouse X in waveform container: ", elX);
  }, [elX])
 
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (!file.processed) {
      interval = setInterval(() => {
        setFakeWaveformPerc(prev => {
          if (prev >= 100) return 100;
          return prev + Math.random() * 10;
        });
      }, 750);
    } else {
      setFakeWaveformPerc(100);
    }
    return () => {
      if (interval) clearInterval(interval);
    }
  }, [file.processed]);

  const str = file.file.filename;
  let hash = 0;
  for (let i = 0; i < str.length; i++) hash = str.charCodeAt(i) + ((hash << 5) - hash);
  const waveformIdx = Math.abs(hash % waveformImages.length);

  const { audio, controls, state } = useAudioFile(file.file.file as File);

  const playAt = () => {
    if (!waveformContainerRef.current) return;
    const rect = waveformContainerRef.current.getBoundingClientRect();
    const clickX = elX;
    const perc = clickX / rect.width;
    const time = perc * state.duration;
    controls.play();
    controls.seek(time);
  }

  return (
    <div key={file.file.filename} className="w-full">
      {audio}
      <div className="w-full flex items-center justify-between">
        <div className="flex gap-2 items-center">
          <p className="text-xs line-clamp-2 text-ellipsis leading-tight">{file.file.filenameWithoutExtension}</p>

          <span className="cursor-pointer" onClick={() => state.playing ? controls.pause() : controls.play()}>
            <AnimatePresence mode="popLayout">
              {state.playing ? (
                <motion.span key="pause" initial={{ scale: 0 }} animate={{ scale: 1 }} exit={{ scale: 0 }}>
                  <Pause size={14}></Pause>
                </motion.span>
              ) : (
                <motion.span key="play" initial={{ scale: 0 }} animate={{ scale: 1 }} exit={{ scale: 0 }}>
                  <Play size={14}></Play>
                </motion.span>
              )}
            </AnimatePresence>
          </span>
        </div>

        <p className="text-xs opacity-75">{Math.floor(state.duration/60)}:{Math.floor(state.duration % 60).toString().padStart(2, "0")}</p>
      </div>
      <div ref={waveformContainerRef} className="waveform relative w-full h-7" onClick={playAt}>
        <AnimatePresence>
          {file.processed ? (
            <motion.img
              // Real waveform
              key="real"
              // TODO: Fix stretching
              className="w-full h-full absolute top-0 left-0"
              src={file.processed?.waveform_data}
              alt={file.file.filename + " waveform"}
              initial={{ opacity: 0, scale: 0.5 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.05, delay: 0.25, type:"spring", stiffness: 50, damping: 10 }}
            ></motion.img>
          ) : (
            <motion.img 
              // Fake waveform
              key="fake"
              className="w-full h-full absolute top-0 left-0 blur-[2px] z-20"
              src={waveformImages[waveformIdx]}
              alt={file.file.filename + " waveform loading"}
              exit={{ opacity: 0}}
              transition={{ duration: 0.3 }}
              animate={{ clipPath: `inset(0% ${100 - Math.min(fakeWaveformPerc, 100)}% 0% 0%)` }}
            ></motion.img>
          )}
        </AnimatePresence>

        {/* User playhead */}
        <motion.div 
          className="absolute w-[2px] top-1 left-0 bottom-1 bg-white opacity-75 rounded-full"
          style={{ marginLeft: elX }}
          initial={{ opacity: 0 }}
          animate={{ opacity: waveformHovered ? 1 : 0 }}
        ></motion.div>

        {/* State playhead */}
        <motion.div 
          className="absolute w-[2px] top-1 left-0 bottom-1 bg-white rounded-full"
          initial={{ opacity: 0 }}
          animate={{ 
            opacity: state.playing ? 0.5 : 0,
            marginLeft: (state.time / state.duration * 100) + "%"
          }}
        ></motion.div>
      </div>
      <Select defaultValue={file.model} onValueChange={value => {file.model = value as SpleeterModel; console.log(file.model)}} disabled={!file.processed}>
        <SelectTrigger size="sm" className="p-1 z-50">
          <SelectValue placeholder="STEM model"></SelectValue>
        </SelectTrigger>
        <SelectContent>
          <SelectGroup>
            <SelectLabel>STEM model</SelectLabel>
            {Object.keys(SpleeterModels).map((model: SpleeterModel) => (
              <SelectItem key={model} value={model}>{SpleeterModels[model].displayName} <span className="opacity-75 text-xs">({SpleeterModels[model].description})</span></SelectItem>
            ))}
          </SelectGroup>
        </SelectContent>
      </Select>
    </div>
  )
}

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
  const [files, setFiles] = useState<FileWrapper[]>([]);

  useEffect(() => {
    console.log("Files: ", files);
  }, [files]);

  // TODO: Consider using useReducer
  const addFile = (_err: FilePondErrorDescription | null, file: FilePondFile) => {
    
    setFiles(prev => {
      console.log("Attempting to add file:", files.length);
      if (files.length > maxFiles) {
        console.log("Max files reached: ", files.length);
        return;
      }

      const wrapper = new FileWrapper(file);
      const newArr = Array.from(new Set([...prev, wrapper].slice(0, maxFiles)));

      console.log("Adding file:", file);
      console.log("Pywebview ready:", !!pywebview);

      // TODO: STILL SENDS OVERFLOWN FILES WHEN ADDED QUICKLY 😭
    if (newArr.includes(wrapper)) {
      setStatus(`Processing files...`);
      console.log("Sending file to Python:", file.filename, file.id);
      toBase64(file.file as File).then(data => {
        window.pywebview.api.addFile<FileProcessResult>({
          filename: file.filename,
          id: file.id,
          data
        }).then(res => {
          // Update the processed file in state
          setFiles(prev => prev.map(f => {
            if (f === wrapper) return new FileWrapper(f.file, res);
            return f;
          }));
          setStatus(`File processed successfully.`);
          console.log("File processed successfully");
          return res;
        }).then(console.log);
      }).then(() => {
        console.log("File sent to Python successfully.");
        
      });
    }

      return newArr;
    });
  };

  const removeFile = (_err: FilePondErrorDescription | null, file: FilePondFile) => {
    setFiles(prev => prev.filter(f => f.file.file !== file.file));
    console.log("Removing file:", file.filename);
    console.log(files);
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
                  files={files.map(f => f.file.file)}
                  onaddfile={addFile}
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
            <div className="w-full h-full overflow-hidden flex flex-col gap-2 p-4">
              {files.map(file => <FilePreview key={file.file.filename} file={file}></FilePreview>)}
            </div>

            <div className="w-full flex justify-between p-6 absolute bottom-0 right-0">
              <Button onClick={() => setStep("file-select")} variant="outline">Back</Button>
              <Button onClick={() => setStep("separate")}>Next</Button>
            </div>
          </TabsContent>

          <TabsContent value="separate" className="w-full h-full">
            <div className="w-full h-full flex items-center justify-center">
              <p>Separation in progress...</p>
            </div>
            <div className="w-full flex justify-between p-6 absolute bottom-0 right-0">
              <Button onClick={() => setStep("settings")} variant="outline">Back</Button>
              <Button disabled>Start Separation</Button>
            </div>
          </TabsContent>
        </TabsContents>
      </Tabs>
    </div>
  )
}