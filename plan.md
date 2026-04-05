# Plan to Address Professor's Feedback on Appendix Listings

## Objective
The professor wants to ensure that no single listing (code snippet) in the appendix is split across two pages. He is okay with the appendix overall spanning multiple pages, and he is okay with reducing the font size of the listings so that an individual listing is small enough to fit on a single page without breaking.

## Proposed Strategy

1. **Reduce Listing Font Size Globally and Locally:**
   - Modified the global `\lstset` configuration in the document preamble changing it to `\scriptsize`.
   - The longest listings in the Appendix (like `lst:sparql-usn` at 58 lines) still will not fit on one page under the `elsarticle` `review` option (which enforces double-spacing). 
   - We specifically inject `\lstset{basicstyle=\tiny\ttfamily}` immediately after `\appendix` in `main.tex` to make sure these massive appendix blocks shrink enough to fit on one page.

2. **Prevent Page Breaks within Individual Listings:**
   - We wrap each `lstlisting` block in the Appendix inside a `minipage` environment.
   - Since a `minipage` cannot be broken across pages, LaTeX will automatically move the entire listing to the next page if it doesn't fit on the current one.
   - **Note on `\samepage` and `mdframed`**: `minipage` alone is sufficient to prevent page breaks _provided_ the content actually fits on a single page margin. The reason the page break issue persisted was that the 58-line listing exceeded `\textheight`. By dropping the font size to `\tiny`, it will now fit within the `minipage` on a single page.

## Implementation Details for `Paper/main.tex`

1. **Update `\lstset` in Appendix:**
   ```latex
   \appendix
   \lstset{basicstyle=\tiny\ttfamily}
   \section{...}
   ```
2. **Keep `minipage` around listings:**
   ```latex
   \begin{minipage}{\linewidth}
   \begin{lstlisting}[caption={...}, label={...}]
   ...
   \end{lstlisting}
   \end{minipage}
   ```
