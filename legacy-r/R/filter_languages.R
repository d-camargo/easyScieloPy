#' Normalize and validate article language codes
#'
#' Accepts a single language code ("es", "pt", "en") and validates it.
#'
#' @param lang_code A character vector of length 1. Language code to filter by.
#'
#' @return A normalized (lowercase) language code if valid.
#' @export
#'
#' @examples
#' normalize_languages("EN")  # returns "en"
normalize_languages <- function(lang_code) {
  if (length(lang_code) != 1) {
    stop("Only one article language is supported. Provide a single language code ('es', 'pt', 'en').", call. = FALSE)
  }
  
  if (!is.character(lang_code)) {
    stop("The language code must be a character string.", call. = FALSE)
  }
  
  lang_code <- tolower(trimws(lang_code))
  
  allowed_langs <- c("es", "pt", "en")
  if (!lang_code %in% allowed_langs) {
    stop(sprintf("Invalid language code: '%s'. Allowed values are: %s.",
                 lang_code, paste(allowed_langs, collapse = ", ")), call. = FALSE)
  }
  
  return(lang_code)
}
