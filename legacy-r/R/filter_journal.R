#' Normalize and validate a journal name
#'
#' Accepts a single journal name and validates it.
#'
#' @param journal A character vector of length 1. Journal name to filter by (e.g., "Revista Ambiente & Água").
#'
#' @return A cleaned journal name if valid.
#' @export
#'
#'
normalize_journals <- function(journal) {
  if (length(journal) != 1) {
    stop("Only one journal name is supported. Provide a single journal string.", call. = FALSE)
  }
  
  if (!is.character(journal)) {
    stop("The journal name must be a character string.", call. = FALSE)
  }
  
  journal <- trimws(journal)
  
  if (nchar(journal) < 2) {
    stop("The journal name must be at least 2 characters long.", call. = FALSE)
  }
  
  return(journal)
}
