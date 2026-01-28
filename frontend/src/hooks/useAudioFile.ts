import { useEffect, useState } from "react";
import { useAudio } from "react-use";
import { HTMLMediaProps } from "react-use/lib/factory/createHTMLMediaHook";

export default function useAudioFile(file: File, props?: HTMLMediaProps) {
    const [loaded, setLoaded] = useState(false);
    const [error, setError] = useState<ProgressEvent<FileReader> | null>(null);
    const [source, setSource] = useState<string | null>(null);

    useEffect(() => {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = () => {
            setSource(reader.result as string);
        };
        reader.onerror = setError;
        reader.onloadend = () => {
            setLoaded(true);
        };

        () => reader.abort();
    }, [file]);

    const [audio, state, controls, ref] = useAudio({ src: source, ...props });

    return { loaded, error, source, audio, state, controls, ref };
}