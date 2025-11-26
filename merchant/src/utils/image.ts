const HTTP_PROTOCOL_REGEX = /^https?:\/\//i;

export const toRelativeImageUrl = (url?: string | null): string => {
  if (!url) {
    return '';
  }

  if (url.startsWith('/')) {
    return url;
  }

  if (HTTP_PROTOCOL_REGEX.test(url)) {
    try {
      const parsed = new URL(url);
      const pathname = parsed.pathname || '/';
      const search = parsed.search || '';
      const hash = parsed.hash || '';
      return `${pathname}${search}${hash}`;
    } catch {
      return url;
    }
  }

  const sanitized = url.replace(/^\/+/, '');
  return `/${sanitized}`;
};

export const normalizeImageList = (images?: string[]) =>
  (images || [])
    .map(toRelativeImageUrl)
    .filter((item): item is string => Boolean(item));

