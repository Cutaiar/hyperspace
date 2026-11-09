import { useCallback, useEffect, useRef, useState } from 'react'

/** State that a non-React render loop can read without re-rendering.
 *
 *  The loop reads `ref.current`; React renders from `value`. The two are kept
 *  in step by one effect with one dependency -- the whole object -- so adding
 *  a field cannot silently fail to reach the loop. That was the live hazard in
 *  the first port: engine fields were mirrored one at a time through a
 *  dependency list, and a control added without its entry there would render,
 *  move, and do nothing, with nothing to catch it.
 *
 *  `onChange` fires after each sync, which is where the loop gets told its
 *  output is stale.
 */
export function useMirror<T extends object>(initial: T, onChange?: (v: T) => void) {
  const [value, setValue] = useState<T>(initial)
  const ref = useRef<T>(initial)
  const cb = useRef(onChange)
  cb.current = onChange

  useEffect(() => { ref.current = value; cb.current?.(value) }, [value])

  /** Merge a partial update. Narrow by construction: only keys of T compile. */
  const patch = useCallback(
    (p: Partial<T> | ((prev: T) => Partial<T>)) =>
      setValue(prev => ({ ...prev, ...(typeof p === 'function' ? p(prev) : p) })),
    [])

  return { value, ref, patch, set: setValue } as const
}
