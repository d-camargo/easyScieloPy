#' Normalize and validate a subject category
#'
#' Accepts a single subject category and validates it.
#'
#' @param category A character vector of length 1. Subject category to filter by (e.g., "environmental sciences").
#'
#' @return A cleaned category string if valid.
#' @export
#'
#'
normalize_categories <- function(category) {
  if (length(category) != 1) {
    stop("Only one subject category is supported. Provide a single category string.", call. = FALSE)
  }
  
  if (!is.character(category)) {
    stop("The subject category must be a character string.", call. = FALSE)
  }
  
  category <- trimws(category)
  
  if (nchar(category) < 2) {
    stop("The subject category must be at least 2 characters long.", call. = FALSE)
  }
  
  return(category)
}
