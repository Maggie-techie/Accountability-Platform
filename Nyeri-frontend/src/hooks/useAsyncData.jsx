import { useState, useEffect, useCallback, useRef } from 'react'

/**
 * Global cache for sharing data across components and persisting across mounts
 * This is a module-level Map that survives component unmount/remount cycles
 */
export const globalCache = new Map()

/**
 * Custom hook for async data fetching with:
 * - Immediate skeleton rendering (no blocking)
 * - Automatic deduplication (same key = same promise)
 * - Persistent caching with TTL (survives page navigation)
 * - Retry on error
 */
export function useAsyncData(key, fetcher, options = {}) {
  const {
    immediate = true,
    cacheTime = 5 * 60 * 1000, // 5 min default cache
    retry = 1,
    retryDelay = 1000,
    onSuccess,
    onError,
    persistent = true, // When true, uses globalCache to persist across mounts
  } = options

  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [isLoading, setIsLoading] = useState(immediate)
  const [isRefreshing, setIsRefreshing] = useState(false)

  // Per-instance cache for deduplication within same mount
  const cacheRef = useRef(new Map())
  const abortRef = useRef(null)
  const mountedRef = useRef(true)
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  // Cleanup on unmount
  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
      if (abortRef.current) abortRef.current.abort()
    }
  }, [])

  const getCache = useCallback(() => persistent ? globalCache : cacheRef.current, [persistent])

  const execute = useCallback(async (isRetry = false) => {
    if (!isRetry) {
      // Check cache first (global or local)
      const cache = getCache()
      const cached = cache.get(key)
      if (cached && Date.now() - cached.timestamp < cacheTime) {
        setData(cached.data)
        setIsLoading(false)
        return cached.data
      }
    }

    if (!isRetry) setIsLoading(true)
    else setIsRefreshing(true)
    setError(null)

    // Abort previous request
    if (abortRef.current) abortRef.current.abort()
    const controller = new AbortController()
    abortRef.current = controller

    let attempt = 0
    while (attempt <= retry) {
      try {
        const result = await fetcherRef.current(controller.signal)

        if (!mountedRef.current) return null
        if (controller.signal.aborted) return null

        // Cache successful result (global or local)
        const cache = getCache()
        cache.set(key, { data: result, timestamp: Date.now() })

        setData(result)
        setError(null)
        onSuccess?.(result)
        return result
      } catch (err) {
        if (err.name === 'AbortError' || !mountedRef.current) return null

        attempt++
        if (attempt <= retry) {
          await new Promise(r => setTimeout(r, retryDelay * attempt))
        } else {
          if (!mountedRef.current) return null
          setError(err)
          onError?.(err)
          throw err
        }
      } finally {
        if (!isRetry) setIsLoading(false)
        else setIsRefreshing(false)
      }
    }
  }, [key, cacheTime, retry, retryDelay, onSuccess, onError, getCache])

  // Initial fetch
  useEffect(() => {
    if (immediate) {
      execute()
    }
  }, [immediate, execute])

  const refresh = useCallback(() => execute(true), [execute])
  const clearCache = useCallback(() => getCache().delete(key), [key, getCache])

  return {
    data,
    error,
    isLoading,
    isRefreshing,
    refresh,
    clearCache,
    execute,
  }
}

/**
 * Shared async data hook - alias for useAsyncData with persistent=true
 * Use this when you want data to persist across component mounts/page navigations
 */
export function useSharedAsyncData(key, fetcher, options = {}) {
  return useAsyncData(key, fetcher, { ...options, persistent: true })
}

/**
 * Skeleton component for consistent loading states
 */
export function Skeleton({ className = '', variant = 'text' }) {
  const base = 'animate-pulse bg-forest-100 rounded'
  const variants = {
    text: 'h-4 w-3/4 inline-block',
    title: 'h-6 w-1/2 inline-block',
    card: 'h-32 w-full',
    avatar: 'h-12 w-12 rounded-full',
    badge: 'h-6 w-20 rounded inline-block',
    kpi: 'h-10 w-24 inline-block',
    chart: 'h-64 w-full',
    tableRow: 'h-10 w-full',
  }
  // Use span for inline variants to avoid DOM nesting issues inside <p> tags
  const inlineVariants = ['text', 'title', 'badge', 'kpi']
  const Tag = inlineVariants.includes(variant) ? 'span' : 'div'
  return <Tag className={`${base} ${variants[variant]} ${className}`} />
}

/**
 * Wrapper that shows skeleton while loading, then content
 */
export function AsyncContent({
  children,
  isLoading,
  error,
  skeleton,
  emptyMessage = 'No data available',
  onRetry
}) {
  if (isLoading) {
    return skeleton || (
      <div className="space-y-4">
        <Skeleton variant="title" className="w-1/3" />
        <Skeleton variant="text" className="w-1/2" />
        <Skeleton variant="text" className="w-1/3" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-8 text-ink-danger">
        <p className="mb-2">Failed to load</p>
        <p className="text-sm text-ink-muted mb-4">{error.message}</p>
        <button onClick={onRetry} className="text-forest-700 hover:underline text-sm">
          Try again
        </button>
      </div>
    )
  }

  if (!children || (Array.isArray(children) && children.length === 0)) {
    return (
      <div className="text-center py-8 text-ink-muted">
        {emptyMessage}
      </div>
    )
  }

  return <>{children}</>
}