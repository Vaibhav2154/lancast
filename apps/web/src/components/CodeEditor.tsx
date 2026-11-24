import { useMemo } from "react";
import CodeMirror from "@uiw/react-codemirror";
import { python } from "@codemirror/lang-python";
import { cpp } from "@codemirror/lang-cpp";
import { java } from "@codemirror/lang-java";
import { javascript } from "@codemirror/lang-javascript";
import { HighlightStyle, syntaxHighlighting } from "@codemirror/language";
import { EditorView } from "@codemirror/view";
import { tags as t } from "@lezer/highlight";
import type { Theme } from "../hooks/useTheme";

const lightBase = EditorView.theme(
  {
    "&": {
      backgroundColor: "#FFFFFF",
      color: "#171717",
      fontSize: "13.5px",
      fontFamily: "var(--font-mono)",
    },
    ".cm-scroller": {
      lineHeight: "1.65",
      fontFamily: "var(--font-mono)",
      padding: "8px 0",
    },
    ".cm-content": {
      caretColor: "#0E9F58",
      padding: "4px 0",
    },
    ".cm-cursor, .cm-dropCursor": {
      borderLeftColor: "#0E9F58",
      borderLeftWidth: "2px",
    },
    "&.cm-focused .cm-selectionBackground, .cm-selectionBackground, .cm-content ::selection": {
      backgroundColor: "rgba(14, 159, 88, 0.18)",
    },
    ".cm-activeLine": {
      backgroundColor: "#ECFDF5",
    },
    ".cm-gutters": {
      backgroundColor: "#F5F7F6",
      color: "#737373",
      borderRight: "1px solid #D8E3DD",
      paddingRight: "6px",
    },
    ".cm-activeLineGutter": {
      backgroundColor: "#E4F3EA",
      color: "#047857",
      fontWeight: "700",
    },
    ".cm-matchingBracket": {
      backgroundColor: "rgba(14, 159, 88, 0.22)",
      outline: "1px solid rgba(14, 159, 88, 0.45)",
      color: "#047857",
    },
    ".cm-placeholder": {
      color: "#737373",
    },
  },
  { dark: false }
);

const darkBase = EditorView.theme(
  {
    "&": {
      backgroundColor: "#0A0A0A",
      color: "#F5F5F5",
      fontSize: "13.5px",
      fontFamily: "var(--font-mono)",
    },
    ".cm-scroller": {
      lineHeight: "1.65",
      fontFamily: "var(--font-mono)",
      padding: "8px 0",
    },
    ".cm-content": {
      caretColor: "#34D399",
      padding: "4px 0",
    },
    ".cm-cursor, .cm-dropCursor": {
      borderLeftColor: "#34D399",
      borderLeftWidth: "2px",
    },
    "&.cm-focused .cm-selectionBackground, .cm-selectionBackground, .cm-content ::selection": {
      backgroundColor: "rgba(16, 185, 129, 0.24)",
    },
    ".cm-activeLine": {
      backgroundColor: "rgba(16, 185, 129, 0.08)",
    },
    ".cm-gutters": {
      backgroundColor: "#121212",
      color: "#525252",
      borderRight: "1px solid #262626",
      paddingRight: "6px",
    },
    ".cm-activeLineGutter": {
      backgroundColor: "#1A1A1A",
      color: "#34D399",
      fontWeight: "700",
    },
    ".cm-matchingBracket": {
      backgroundColor: "rgba(52, 211, 153, 0.22)",
      outline: "1px solid rgba(52, 211, 153, 0.5)",
      color: "#6EE7B7",
    },
    ".cm-placeholder": {
      color: "#525252",
    },
  },
  { dark: true }
);

const lightHighlight = syntaxHighlighting(
  HighlightStyle.define([
    { tag: [t.keyword, t.controlKeyword, t.operatorKeyword], color: "#047857", fontWeight: "700" },
    { tag: [t.string, t.special(t.string)], color: "#0F766E" },
    { tag: [t.function(t.variableName), t.function(t.propertyName)], color: "#1D4ED8" },
    { tag: [t.number, t.bool, t.null, t.atom], color: "#B45309" },
    { tag: [t.typeName, t.className, t.namespace], color: "#6D28D9" },
    { tag: [t.comment, t.lineComment, t.blockComment], color: "#737373", fontStyle: "italic" },
    { tag: [t.operator, t.punctuation], color: "#404040" },
    { tag: t.variableName, color: "#171717" },
  ])
);

const darkHighlight = syntaxHighlighting(
  HighlightStyle.define([
    { tag: [t.keyword, t.controlKeyword, t.operatorKeyword], color: "#34D399", fontWeight: "700" },
    { tag: [t.string, t.special(t.string)], color: "#A7F3D0" },
    { tag: [t.function(t.variableName), t.function(t.propertyName)], color: "#60A5FA" },
    { tag: [t.number, t.bool, t.null, t.atom], color: "#FBBF24" },
    { tag: [t.typeName, t.className, t.namespace], color: "#C4B5FD" },
    { tag: [t.comment, t.lineComment, t.blockComment], color: "#737373", fontStyle: "italic" },
    { tag: [t.operator, t.punctuation], color: "#D4D4D4" },
    { tag: t.variableName, color: "#F5F5F5" },
  ])
);

function languageExtension(language: string) {
  switch (language) {
    case "python3":
      return python();
    case "c":
    case "cpp":
      return cpp();
    case "java":
      return java();
    case "javascript":
      return javascript();
    default:
      return python();
  }
}

export function CodeEditor({
  value,
  language,
  theme,
  onChange,
  placeholder,
  minHeight = "320px",
}: {
  value: string;
  language: string;
  theme: Theme;
  onChange: (value: string) => void;
  placeholder?: string;
  minHeight?: string;
}) {
  const extensions = useMemo(() => [languageExtension(language)], [language]);
  const cmTheme = useMemo(
    () => (theme === "dark" ? [darkBase, darkHighlight] : [lightBase, lightHighlight]),
    [theme]
  );

  return (
    <CodeMirror
      value={value}
      minHeight={minHeight}
      theme={cmTheme}
      extensions={extensions}
      onChange={onChange}
      placeholder={placeholder}
      indentWithTab={true}
      basicSetup={{
        lineNumbers: true,
        highlightActiveLineGutter: true,
        highlightActiveLine: true,
        foldGutter: true,
        bracketMatching: true,
        closeBrackets: true,
        indentOnInput: true,
        history: true,
        searchKeymap: true,
        tabSize: 4,
        autocompletion: false,
        completionKeymap: false,
      }}
    />
  );
}
