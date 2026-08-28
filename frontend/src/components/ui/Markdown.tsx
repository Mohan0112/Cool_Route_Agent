import ReactMarkdown from "react-markdown"

/** Agent text fields naturally come back as markdown (bold ranks, numbered lists) --
 * render it properly rather than fighting the model to suppress formatting it wants to use. */
export function Markdown({ children }: { children: string }) {
  return (
    <div className="prose-sm max-w-none space-y-2 text-sm text-[var(--text)] [&_strong]:text-[var(--text)] [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&_h3]:text-sm [&_h3]:font-semibold">
      <ReactMarkdown>{children}</ReactMarkdown>
    </div>
  )
}
