<#import "field.ftl" as field>
<#import "footer.ftl" as loginFooter>
<#macro username>
  <#assign label>
    <#if !realm.loginWithEmailAllowed>${msg("username")}<#elseif !realm.registrationEmailAsUsername>${msg("usernameOrEmail")}<#else>${msg("email")}</#if>
  </#assign>
  <@field.group name="username" label=label>
    <div class="${properties.kcInputGroup}">
      <div class="${properties.kcInputGroupItemClass} ${properties.kcFill}">
        <span class="${properties.kcInputClass} ${properties.kcFormReadOnlyClass}">
          <input id="kc-attempted-username" value="${auth.attemptedUsername}" readonly>
        </span>
      </div>
      <div class="${properties.kcInputGroupItemClass}">
        <button id="reset-login" class="${properties.kcFormPasswordVisibilityButtonClass} kc-login-tooltip" type="button"
              aria-label="${msg('restartLoginTooltip')}" onclick="location.href='${url.loginRestartFlowUrl}'">
            <i class="fa-sync-alt fas" aria-hidden="true"></i>
            <span class="kc-tooltip-text">${msg("restartLoginTooltip")}</span>
        </button>
      </div>
    </div>
  </@field.group>
</#macro>

<#macro registrationLayout bodyClass="" displayInfo=false displayMessage=true displayRequiredFields=false>
<!DOCTYPE html>
<html class="${properties.kcHtmlClass!}" lang="${lang}"<#if realm.internationalizationEnabled> dir="${(locale.rtl)?then('rtl','ltr')}"</#if>>

<head>
    <meta charset="utf-8">
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
    <meta name="robots" content="noindex, nofollow">
    <meta name="color-scheme" content="dark">
    <meta name="viewport" content="width=device-width, initial-scale=1">

    <#if properties.meta?has_content>
        <#list properties.meta?split(' ') as meta>
            <meta name="${meta?split('==')[0]}" content="${meta?split('==')[1]}"/>
        </#list>
    </#if>
    <title>${msg("loginTitle",(realm.displayName!''))}</title>
    <link rel="icon" href="${url.resourcesPath}/img/favicon.ico" />

    <style>
      @font-face {
        font-family: 'Geist Variable';
        src: url('${url.resourcesPath}/fonts/geist-latin-wght-normal.woff2') format('woff2');
        font-weight: 100 900;
        font-display: swap;
      }
    </style>

    <#if properties.stylesCommon?has_content>
        <#list properties.stylesCommon?split(' ') as style>
            <link href="${url.resourcesCommonPath}/${style}" rel="stylesheet" />
        </#list>
    </#if>
    <#if properties.styles?has_content>
        <#list properties.styles?split(' ') as style>
            <link href="${url.resourcesPath}/${style}" rel="stylesheet" />
        </#list>
    </#if>
    <script type="importmap">
        {
            "imports": {
                "rfc4648": "${url.resourcesCommonPath}/vendor/rfc4648/rfc4648.js"
            }
        }
    </script>
    <#if properties.scripts?has_content>
        <#list properties.scripts?split(' ') as script>
            <script src="${url.resourcesPath}/${script}" type="text/javascript"></script>
        </#list>
    </#if>
    <#if scripts??>
        <#list scripts as script>
            <script src="${script}" type="text/javascript"></script>
        </#list>
    </#if>
    <script type="module" src="${url.resourcesPath}/js/passwordVisibility.js"></script>
    <script type="module">
        import { startSessionPolling } from "${url.resourcesPath}/js/authChecker.js";
        startSessionPolling("${url.ssoLoginInOtherTabsUrl?no_esc}");
    </script>
    <#if authenticationSession??>
        <script type="module">
            import { checkAuthSession } from "${url.resourcesPath}/js/authChecker.js";
            checkAuthSession("${authenticationSession.authSessionIdHash}");
        </script>
    </#if>
    <script>const isFirefox = true;</script>
</head>

<body id="keycloak-bg" class="${properties.kcBodyClass!}" data-page-id="login-${pageId}">

<!-- ═══ Animated topology background ═══ -->
<div class="nx-backdrop" aria-hidden="true">
  <!-- Grid pattern -->
  <svg class="nx-grid" viewBox="0 0 800 600" preserveAspectRatio="xMidYMid slice">
    <defs>
      <pattern id="nx-dot-grid" x="0" y="0" width="40" height="40" patternUnits="userSpaceOnUse">
        <circle cx="20" cy="20" r="0.8" fill="rgba(99,102,241,0.15)"/>
      </pattern>
      <linearGradient id="nx-line-grad" x1="0%" y1="0%" x2="100%" y2="0%">
        <stop offset="0%" stop-color="transparent"/>
        <stop offset="30%" stop-color="rgba(99,102,241,0.25)"/>
        <stop offset="70%" stop-color="rgba(129,140,248,0.2)"/>
        <stop offset="100%" stop-color="transparent"/>
      </linearGradient>
      <linearGradient id="nx-vert-grad" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stop-color="transparent"/>
        <stop offset="40%" stop-color="rgba(99,102,241,0.12)"/>
        <stop offset="60%" stop-color="rgba(192,132,252,0.08)"/>
        <stop offset="100%" stop-color="transparent"/>
      </linearGradient>
      <radialGradient id="nx-node-glow" cx="50%" cy="50%" r="50%">
        <stop offset="0%" stop-color="rgba(129,140,248,0.6)"/>
        <stop offset="100%" stop-color="transparent"/>
      </radialGradient>
      <filter id="nx-blur">
        <feGaussianBlur in="SourceGraphic" stdDeviation="1.5"/>
      </filter>
    </defs>
    <rect width="800" height="600" fill="url(#nx-dot-grid)"/>
    <!-- Horizontal data flow lines -->
    <line x1="0" y1="150" x2="800" y2="150" stroke="url(#nx-line-grad)" stroke-width="0.5" class="nx-flow-h nx-flow-h-1"/>
    <line x1="0" y1="300" x2="800" y2="300" stroke="url(#nx-line-grad)" stroke-width="0.5" class="nx-flow-h nx-flow-h-2"/>
    <line x1="0" y1="450" x2="800" y2="450" stroke="url(#nx-line-grad)" stroke-width="0.5" class="nx-flow-h nx-flow-h-3"/>
    <!-- Vertical lines -->
    <line x1="200" y1="0" x2="200" y2="600" stroke="url(#nx-vert-grad)" stroke-width="0.5"/>
    <line x1="400" y1="0" x2="400" y2="600" stroke="url(#nx-vert-grad)" stroke-width="0.5"/>
    <line x1="600" y1="0" x2="600" y2="600" stroke="url(#nx-vert-grad)" stroke-width="0.5"/>
    <!-- Data nodes at intersections -->
    <circle cx="200" cy="150" r="3" fill="rgba(99,102,241,0.4)" class="nx-node nx-node-1"/>
    <circle cx="600" cy="150" r="2.5" fill="rgba(52,211,153,0.4)" class="nx-node nx-node-2"/>
    <circle cx="200" cy="450" r="2" fill="rgba(244,114,182,0.35)" class="nx-node nx-node-3"/>
    <circle cx="600" cy="450" r="3" fill="rgba(251,191,36,0.35)" class="nx-node nx-node-4"/>
    <circle cx="400" cy="300" r="4" fill="rgba(129,140,248,0.3)" class="nx-node nx-node-5" filter="url(#nx-blur)"/>
    <!-- Flowing data particles -->
    <circle r="1.5" fill="#818CF8" class="nx-particle nx-particle-1">
      <animateMotion dur="6s" repeatCount="indefinite" path="M0,150 L800,150"/>
    </circle>
    <circle r="1.2" fill="#34D399" class="nx-particle nx-particle-2">
      <animateMotion dur="8s" repeatCount="indefinite" path="M0,300 L800,300"/>
    </circle>
    <circle r="1" fill="#C084FC" class="nx-particle nx-particle-3">
      <animateMotion dur="7s" repeatCount="indefinite" path="M0,450 L800,450"/>
    </circle>
    <circle r="1.3" fill="#818CF8" class="nx-particle nx-particle-4">
      <animateMotion dur="9s" repeatCount="indefinite" path="M200,0 L200,600"/>
    </circle>
    <circle r="1" fill="#F472B6" class="nx-particle nx-particle-5">
      <animateMotion dur="7.5s" repeatCount="indefinite" path="M600,0 L600,600"/>
    </circle>
  </svg>

  <!-- Radial glow -->
  <div class="nx-glow"></div>
  <div class="nx-glow nx-glow-secondary"></div>

  <!-- Scan line -->
  <div class="nx-scanline"></div>
</div>

<!-- ═══ Main login layout ═══ -->
<div class="nx-login-shell">
  <div class="nx-login-container">

    <!-- Branding -->
    <header class="nx-brand" id="kc-header">
      <div class="nx-brand-inner" id="kc-header-wrapper">
        <div class="nx-logo-orb">
          <div class="nx-logo-ring"></div>
          <div class="nx-logo-ring nx-logo-ring-2"></div>
          <img src="${url.resourcesPath}/img/logo.svg" alt="ETL Nexus" class="nx-logo-img" />
        </div>
        <div class="nx-brand-text">
          <h1 class="nx-title">ETL Nexus</h1>
          <p class="nx-subtitle">Data Intelligence Command Center</p>
        </div>
      </div>
    </header>

    <!-- Card -->
    <main class="nx-card ${properties.kcLoginMain!}">
      <div class="nx-card-glow"></div>
      <div class="${properties.kcLoginMainHeader!} nx-card-header">
        <h2 class="nx-card-title" id="kc-page-title"><#nested "header"></h2>
        <#if realm.internationalizationEnabled && locale.supported?size gt 1>
        <div class="${properties.kcLoginMainHeaderUtilities!}">
          <div class="${properties.kcInputClass!}">
            <select aria-label="${msg("languages")}" id="login-select-toggle"
              onchange="if (this.value) window.location.href=this.value">
              <#list locale.supported?sort_by("label") as l>
                <option value="${l.url}" ${(l.languageTag == locale.currentLanguageTag)?then('selected','')}>
                  ${l.label}
                </option>
              </#list>
            </select>
            <span class="${properties.kcFormControlUtilClass}">
              <span class="${properties.kcFormControlToggleIcon!}">
                <svg class="pf-v5-svg" viewBox="0 0 320 512" fill="currentColor" aria-hidden="true" width="1em" height="1em">
                  <path d="M31.3 192h257.3c17.8 0 26.7 21.5 14.1 34.1L174.1 354.8c-7.8 7.8-20.5 7.8-28.3 0L17.2 226.1C4.6 213.5 13.5 192 31.3 192z"/>
                </svg>
              </span>
            </span>
          </div>
        </div>
        </#if>
      </div>

      <div class="${properties.kcLoginMainBody!} nx-card-body">
        <#if !(auth?has_content && auth.showUsername() && !auth.showResetCredentials())>
            <#if displayRequiredFields>
                <div class="${properties.kcContentWrapperClass!}">
                    <div class="${properties.kcLabelWrapperClass!} subtitle">
                        <span class="${properties.kcInputHelperTextItemTextClass!}">
                          <span class="${properties.kcInputRequiredClass!}">*</span> ${msg("requiredFields")}
                        </span>
                    </div>
                </div>
            </#if>
        <#else>
            <#if displayRequiredFields>
                <div class="${properties.kcContentWrapperClass!}">
                    <div class="${properties.kcLabelWrapperClass!} subtitle">
                        <span class="${properties.kcInputHelperTextItemTextClass!}">
                          <span class="${properties.kcInputRequiredClass!}">*</span> ${msg("requiredFields")}
                        </span>
                    </div>
                    <div class="${properties.kcFormClass} ${properties.kcContentWrapperClass}">
                        <#nested "show-username">
                        <@username />
                    </div>
                </div>
            <#else>
                <div class="${properties.kcFormClass} ${properties.kcContentWrapperClass}">
                  <#nested "show-username">
                  <@username />
                </div>
            </#if>
        </#if>

        <#if displayMessage && message?has_content && (message.type != 'warning' || !isAppInitiatedAction??)>
            <div class="${properties.kcAlertClass!} pf-m-${(message.type = 'error')?then('danger', message.type)}">
                <div class="${properties.kcAlertIconClass!}">
                    <#if message.type = 'success'><span class="${properties.kcFeedbackSuccessIcon!}"></span></#if>
                    <#if message.type = 'warning'><span class="${properties.kcFeedbackWarningIcon!}"></span></#if>
                    <#if message.type = 'error'><span class="${properties.kcFeedbackErrorIcon!}"></span></#if>
                    <#if message.type = 'info'><span class="${properties.kcFeedbackInfoIcon!}"></span></#if>
                </div>
                <span class="${properties.kcAlertTitleClass!} kc-feedback-text">${kcSanitize(message.summary)?no_esc}</span>
            </div>
        </#if>

        <#nested "form">

        <#if auth?has_content && auth.showTryAnotherWayLink()>
          <form id="kc-select-try-another-way-form" action="${url.loginAction}" method="post" novalidate="novalidate">
              <input type="hidden" name="tryAnotherWay" value="on"/>
              <a id="try-another-way" href="javascript:document.forms['kc-select-try-another-way-form'].requestSubmit()"
                  class="${properties.kcButtonSecondaryClass} ${properties.kcButtonBlockClass} ${properties.kcMarginTopClass}">
                    ${kcSanitize(msg("doTryAnotherWay"))?no_esc}
              </a>
          </form>
        </#if>

          <div class="${properties.kcLoginMainFooter!}">
              <#nested "socialProviders">
              <#if displayInfo>
                  <div id="kc-info" class="${properties.kcLoginMainFooterBand!} ${properties.kcFormClass}">
                      <div id="kc-info-wrapper" class="${properties.kcLoginMainFooterBandItem!}">
                          <#nested "info">
                      </div>
                  </div>
              </#if>
          </div>
      </div>

      <div class="${properties.kcLoginMainFooter!}">
          <@loginFooter.content/>
      </div>
    </main>

    <!-- Status bar footer -->
    <footer class="nx-status-bar">
      <div class="nx-status-indicator">
        <span class="nx-status-dot"></span>
        <span class="nx-status-text">Made By</span>
      </div>
      <span class="nx-status-text">Itamr Palmon</span>
      <span class="nx-status-divider">/</span>
      <span class="nx-status-text">Keycloak v26.2</span>
    </footer>
  </div>
</div>

</body>
</html>
</#macro>
