#' Normalize and validate n_max
#'
#' Ensures that the value of n_max is a positive integer or NULL.
#'
#' @param value The value to validate.
#' @return An integer or NULL.
#' @keywords internal
normalize_nmax <- function(value) {
  if (is.null(value)) return(NULL)
  
  if (!is.numeric(value) || length(value) != 1 || is.na(value) || value <= 0) {
    stop("The 'n_max' parameter must be a positive numeric value or NULL.", call. = FALSE)
  }
  
  as.integer(value)
}
