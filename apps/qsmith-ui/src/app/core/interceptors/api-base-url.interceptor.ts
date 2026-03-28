import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';

import { RuntimeConfigService } from '../config/runtime-config.service';

export const apiBaseUrlInterceptor: HttpInterceptorFn = (req, next) => {
  if (/^https?:\/\//.test(req.url)) {
    return next(req);
  }

  const runtimeConfig = inject(RuntimeConfigService);
  const baseUrl = runtimeConfig.apiBaseUrl();
  const normalizedBaseUrl = baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl;
  const normalizedPath = req.url.startsWith('/') ? req.url : `/${req.url}`;

  return next(
    req.clone({
      url: `${normalizedBaseUrl}${normalizedPath}`
    })
  );
};
