const HTTP_PROTOCOL_REGEX = /^https?:\/\//i;

export const toRelativeImageUrl = (url?: string | null): string => {
  if (!url) {
    return '';
  }

  if (HTTP_PROTOCOL_REGEX.test(url)) {
    return url;
  }

  if (url.startsWith('/')) {
    return url;
  }

  const sanitized = url.replace(/^\/+/, '');
  return `/${sanitized}`;
};

export const normalizeImageList = (images?: string[]) =>
  (images || [])
    .map(toRelativeImageUrl)
    .filter((item): item is string => Boolean(item));
